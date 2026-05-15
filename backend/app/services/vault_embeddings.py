"""VaultEmbeddingService — TF-IDF semantic search over vault documents.

MVP approach: character n-gram TF-IDF with cosine similarity.
No external API calls needed — works offline and costs zero.
Handles Chinese text via character-level n-grams (no jieba dependency).
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_FILE = "embeddings.json"


@dataclass
class SearchResult:
    """A single search result from the vault."""

    section_title: str
    content: str
    source_document: str
    score: float


@dataclass
class _Section:
    """Internal representation of a vault document section."""

    title: str
    content: str
    source_document: str


@dataclass
class _IndexData:
    """Serializable index data stored in embeddings.json."""

    vocabulary: dict[str, int] = field(default_factory=dict)
    idf: list[float] = field(default_factory=list)
    tfidf_matrix: list[list[float]] = field(default_factory=list)
    sections: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "vocabulary": self.vocabulary,
            "idf": self.idf,
            "tfidf_matrix": self.tfidf_matrix,
            "sections": self.sections,
        }

    @classmethod
    def from_dict(cls, data: dict) -> _IndexData:
        return cls(
            vocabulary=data.get("vocabulary", {}),
            idf=data.get("idf", []),
            tfidf_matrix=data.get("tfidf_matrix", []),
            sections=data.get("sections", []),
        )


def _tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text using character n-grams.

    Strategy:
      - English words: split on whitespace/punctuation, lowercase.
      - Chinese characters: generate bigrams and unigrams.
      - This avoids needing jieba or any external segmentation library.
    """
    tokens: list[str] = []

    # Extract English words (2+ chars)
    english_words = re.findall(r"[a-zA-Z]{2,}", text)
    tokens.extend(w.lower() for w in english_words)

    # Extract Chinese characters
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)

    # Unigrams
    tokens.extend(chinese_chars)

    # Bigrams
    for i in range(len(chinese_chars) - 1):
        tokens.append(chinese_chars[i] + chinese_chars[i + 1])

    return tokens


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency (normalized by total tokens)."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


class VaultEmbeddingService:
    """Manage TF-IDF embeddings for vault documents for semantic retrieval."""

    async def index_vault(self, vault_path: Path) -> int:
        """Generate TF-IDF embeddings for all vault documents.

        Splits each .md file into sections (by ## headings),
        computes TF-IDF vectors, and stores in embeddings.json.

        Returns:
            Number of indexed sections.
        """
        sections = self._collect_sections(vault_path)
        if not sections:
            logger.warning("No sections found in vault: %s", vault_path)
            return 0

        # Build vocabulary and compute TF-IDF
        index_data = self._build_tfidf_index(sections)

        # Save to disk
        embedding_path = vault_path / EMBEDDING_FILE
        embedding_path.write_text(
            json.dumps(index_data.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Indexed %d sections from vault %s", len(sections), vault_path
        )
        return len(sections)

    async def search(
        self, vault_path: Path, query: str, top_k: int = 5
    ) -> list[SearchResult]:
        """Semantic search over vault sections using TF-IDF cosine similarity.

        Args:
            vault_path: Root path of the vault.
            query: Search query string.
            top_k: Number of top results to return.

        Returns:
            Top-k sections with relevance scores.
        """
        embedding_path = vault_path / EMBEDDING_FILE
        if not embedding_path.exists():
            # Auto-index if not yet indexed
            count = await self.index_vault(vault_path)
            if count == 0:
                return []

        raw = json.loads(embedding_path.read_text(encoding="utf-8"))
        index_data = _IndexData.from_dict(raw)

        if not index_data.sections or not index_data.vocabulary:
            return []

        # Compute query TF-IDF vector
        query_tokens = _tokenize(query)
        query_tf = _compute_tf(query_tokens)
        vocab = index_data.vocabulary
        idf = index_data.idf

        query_vec = np.zeros(len(vocab), dtype=np.float64)
        for token, tf_val in query_tf.items():
            if token in vocab:
                idx = vocab[token]
                query_vec[idx] = tf_val * idf[idx]

        query_norm = np.linalg.norm(query_vec)
        if query_norm < 1e-10:
            return []
        query_vec /= query_norm

        # Compute cosine similarities
        tfidf_matrix = np.array(index_data.tfidf_matrix, dtype=np.float64)
        similarities = tfidf_matrix @ query_vec

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results: list[SearchResult] = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score < 1e-6:
                break  # No more relevant results
            section_info = index_data.sections[idx]
            results.append(
                SearchResult(
                    section_title=section_info["title"],
                    content=section_info["content"],
                    source_document=section_info["source_document"],
                    score=score,
                )
            )

        return results

    async def update_document_embedding(
        self, vault_path: Path, doc_path: str
    ) -> None:
        """Re-index a single document after update.

        For simplicity in MVP, this re-indexes the entire vault.
        A future optimization can do incremental updates.
        """
        await self.index_vault(vault_path)

    # ── Private Methods ──────────────────────────────────────────────────

    def _collect_sections(self, vault_path: Path) -> list[_Section]:
        """Walk all .md files in vault and split into sections by ## headings."""
        sections: list[_Section] = []

        if not vault_path.exists():
            return sections

        for md_file in sorted(vault_path.rglob("*.md")):
            rel_path = str(md_file.relative_to(vault_path))

            # Skip the embeddings file itself and any hidden files
            if rel_path.startswith(".") or rel_path == EMBEDDING_FILE:
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                logger.warning("Failed to read %s", md_file)
                continue

            # Strip YAML frontmatter
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    body = parts[2].strip()

            if not body.strip():
                continue

            # Split by ## headings
            file_sections = self._split_by_headings(body, rel_path)
            sections.extend(file_sections)

        return sections

    @staticmethod
    def _split_by_headings(body: str, source_doc: str) -> list[_Section]:
        """Split markdown body into sections by ## headings."""
        sections: list[_Section] = []
        current_title = source_doc  # Default title for content before first heading
        current_lines: list[str] = []

        for line in body.split("\n"):
            if line.startswith("## "):
                # Flush previous section
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append(
                        _Section(
                            title=current_title,
                            content=content,
                            source_document=source_doc,
                        )
                    )
                current_title = line.lstrip("# ").strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Flush last section
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(
                _Section(
                    title=current_title,
                    content=content,
                    source_document=source_doc,
                )
            )

        return sections

    def _build_tfidf_index(self, sections: list[_Section]) -> _IndexData:
        """Build TF-IDF index from sections."""
        # Tokenize all sections
        all_tokens: list[list[str]] = []
        for section in sections:
            combined = f"{section.title} {section.content}"
            all_tokens.append(_tokenize(combined))

        # Build vocabulary
        vocab: dict[str, int] = {}
        for tokens in all_tokens:
            for t in set(tokens):
                if t not in vocab:
                    vocab[t] = len(vocab)

        n_docs = len(sections)
        n_vocab = len(vocab)

        if n_vocab == 0:
            return _IndexData()

        # Compute document frequency
        df = np.zeros(n_vocab, dtype=np.float64)
        for tokens in all_tokens:
            unique_tokens = set(tokens)
            for t in unique_tokens:
                if t in vocab:
                    df[vocab[t]] += 1

        # Compute IDF: log(N / (df + 1)) + 1  (smoothed)
        idf = np.log(n_docs / (df + 1)) + 1

        # Compute TF-IDF matrix (rows = documents, cols = vocabulary)
        tfidf_matrix = np.zeros((n_docs, n_vocab), dtype=np.float64)
        for i, tokens in enumerate(all_tokens):
            tf = _compute_tf(tokens)
            for token, tf_val in tf.items():
                if token in vocab:
                    j = vocab[token]
                    tfidf_matrix[i, j] = tf_val * idf[j]

        # L2-normalize each row
        norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
        norms[norms < 1e-10] = 1.0  # Avoid division by zero
        tfidf_matrix /= norms

        # Build serializable section metadata
        section_metas = [
            {
                "title": s.title,
                "content": s.content,
                "source_document": s.source_document,
            }
            for s in sections
        ]

        return _IndexData(
            vocabulary=vocab,
            idf=idf.tolist(),
            tfidf_matrix=tfidf_matrix.tolist(),
            sections=section_metas,
        )
