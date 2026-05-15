"""ContextHarness — select the RIGHT vault docs, at the RIGHT time, with the RIGHT priority.

This is the critical component that determines which vault documents are injected
into each AI generation call. It operates within a strict token budget to avoid
wasting context window on low-value information.

Phase 1: Static context injection (always-inject + conditional).
Phase 3: Dynamic RAG retrieval via VaultEmbeddingService.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.schemas.vault import ContextPreview

if TYPE_CHECKING:
    from app.services.taste_vault import TasteVault

logger = logging.getLogger(__name__)


@dataclass
class ContextSection:
    """A prioritized section of vault context."""

    name: str
    content: str
    priority: int  # Lower = higher priority (1 = must-have, 5 = nice-to-have)
    source_doc: str

    @property
    def token_estimate(self) -> int:
        return _estimate_tokens(self.content)


@dataclass
class AssemblyPlan:
    """Plan for which sections to include in the context."""

    always_include: list[str] = field(default_factory=list)
    conditional_include: list[str] = field(default_factory=list)
    reason: str = ""


def _estimate_tokens(text: str) -> int:
    """Rough token estimate.

    Chinese text: ~1.5 chars per token.
    English text: ~4 chars per token.
    Mixed content: ~3.5 chars per token (conservative for Chinese-heavy content).
    """
    if not text:
        return 0
    # Heuristic: count CJK characters vs ASCII
    cjk_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    ascii_count = len(text) - cjk_count

    if cjk_count > ascii_count:
        # Primarily Chinese
        return int(len(text) / 1.5)
    return int(len(text) / 3.5)


class ContextHarness:
    """Harness Engineering: select the RIGHT vault docs, at the RIGHT time, with the RIGHT priority."""

    # Context budget: ~4000 tokens for taste context (out of Claude's window)
    MAX_CONTEXT_TOKENS = 4000

    # Documents that are ALWAYS injected (core identity)
    CORE_DOCS = [
        ("style/tone.md", 1),
        ("style/structure.md", 1),
        ("preferences/patterns.md", 2),
        ("context/brand.md", 2),
    ]

    # Documents conditionally injected
    CONDITIONAL_DOCS = [
        ("style/platform-adaptations.md", 3),
        ("competitors/lane-trends.md", 4),
        ("style/vocabulary.md", 3),
        ("context/audience.md", 3),
        ("preferences/explicit-rules.md", 1),  # High priority when present
    ]

    async def assemble_context(
        self,
        vault: "TasteVault",  # noqa: F821
        platform: str,
        topic: str | None = None,
        content_type: str = "post",
    ) -> str:
        """Assemble the context string for a generation call.

        Step 1: ALWAYS inject (core identity)
          - style/tone.md
          - style/structure.md
          - preferences/patterns.md (high-confidence only)
          - context/brand.md

        Step 2: CONDITIONALLY inject (based on task)
          - Platform-specific? -> platform-adaptations.md#[platform]
          - Topic related? -> pull relevant competitor entries
          - Has explicit rules? -> explicit-rules.md

        Step 3: DYNAMIC RAG (topic-aware semantic retrieval)
          - If a topic is provided, search the vault for relevant sections
          - Use TF-IDF cosine similarity to find matching vault content
          - Inject top-k results within remaining token budget

        Step 4: PRIORITY & TRIM
          - Hard rules (explicit-rules.md) > soft preferences
          - Recent edits > old edits
          - High confidence > low confidence
          - Trim to fit MAX_CONTEXT_TOKENS
        """
        if not vault.exists():
            logger.warning("Vault does not exist for %s/%s", vault.user_id, vault.project_slug)
            return ""

        sections: list[ContextSection] = []

        # Step 1: Always-include core docs
        for doc_path, priority in self.CORE_DOCS:
            content = await vault.read_document(doc_path)
            if content:
                _, body = vault._parse_frontmatter(content)
                if body.strip():
                    sections.append(
                        ContextSection(
                            name=doc_path.replace(".md", "").replace("/", " > "),
                            content=body.strip(),
                            priority=priority,
                            source_doc=doc_path,
                        )
                    )

        # Step 2: Conditional docs
        # Explicit rules always go in with highest priority
        rules_content = await vault.read_document("preferences/explicit-rules.md")
        if rules_content:
            _, rules_body = vault._parse_frontmatter(rules_content)
            if rules_body.strip():
                sections.append(
                    ContextSection(
                        name="explicit rules",
                        content=rules_body.strip(),
                        priority=1,
                        source_doc="preferences/explicit-rules.md",
                    )
                )

        # Platform-specific adaptations
        adaptations_content = await vault.read_document("style/platform-adaptations.md")
        if adaptations_content:
            platform_section = self._extract_platform_section(adaptations_content, platform)
            if platform_section:
                sections.append(
                    ContextSection(
                        name=f"platform adaptation ({platform})",
                        content=platform_section,
                        priority=3,
                        source_doc="style/platform-adaptations.md",
                    )
                )

        # Competitor/lane context for topic relevance
        if topic:
            competitor_content = await vault.read_document("competitors/lane-trends.md")
            if competitor_content:
                _, comp_body = vault._parse_frontmatter(competitor_content)
                # Take last 500 chars (most recent trends)
                trimmed = comp_body.strip()[-500:] if comp_body.strip() else ""
                if trimmed:
                    sections.append(
                        ContextSection(
                            name="competitor trends (recent)",
                            content=trimmed,
                            priority=4,
                            source_doc="competitors/lane-trends.md",
                        )
                    )

        # Audience context
        audience_content = await vault.read_document("context/audience.md")
        if audience_content:
            _, audience_body = vault._parse_frontmatter(audience_content)
            if audience_body.strip():
                sections.append(
                    ContextSection(
                        name="audience profile",
                        content=audience_body.strip(),
                        priority=3,
                        source_doc="context/audience.md",
                    )
                )

        # Vocabulary for longer content types
        if content_type in ("article", "thread"):
            vocab_content = await vault.read_document("style/vocabulary.md")
            if vocab_content:
                _, vocab_body = vault._parse_frontmatter(vocab_content)
                if vocab_body.strip():
                    sections.append(
                        ContextSection(
                            name="vocabulary preferences",
                            content=vocab_body.strip(),
                            priority=4,
                            source_doc="style/vocabulary.md",
                        )
                    )

        # Step 3: Dynamic RAG retrieval (topic-aware semantic search)
        if topic:
            rag_sections = await self._dynamic_retrieve(vault, topic, sections)
            sections.extend(rag_sections)

        # Step 4: Prioritize and trim
        return self._prioritize_and_trim(sections, self.MAX_CONTEXT_TOKENS)

    async def preview_context(
        self,
        vault: "TasteVault",  # noqa: F821
        platform: str,
        topic: str | None = None,
        content_type: str = "post",
    ) -> ContextPreview:
        """Preview what context would be assembled (for debugging/admin)."""
        context = await self.assemble_context(vault, platform, topic, content_type)

        # Collect which docs were used
        docs_used: list[str] = []
        for doc_path, _ in self.CORE_DOCS + self.CONDITIONAL_DOCS:
            doc_content = await vault.read_document(doc_path)
            if doc_content and doc_content.strip():
                _, body = vault._parse_frontmatter(doc_content)
                if body.strip() and body.strip()[:50] in context:
                    docs_used.append(doc_path)

        return ContextPreview(
            assembled_context=context,
            token_count=_estimate_tokens(context),
            documents_used=docs_used,
        )

    async def _dynamic_retrieve(
        self,
        vault: "TasteVault",
        topic: str,
        existing_sections: list[ContextSection],
    ) -> list[ContextSection]:
        """RAG: search vault for topic-relevant sections via TF-IDF similarity.

        Returns additional ContextSections that aren't already included from
        the static injection steps.
        """
        from app.services.vault_embeddings import VaultEmbeddingService

        embedding_service = VaultEmbeddingService()

        try:
            results = await embedding_service.search(vault.root, topic, top_k=3)
        except Exception as e:
            logger.warning("Dynamic RAG retrieval failed: %s", e)
            return []

        # Deduplicate: skip sections already included from static injection
        existing_sources = {s.source_doc for s in existing_sections}
        rag_sections: list[ContextSection] = []

        for result in results:
            # Skip if this source document is already in the context
            if result.source_document in existing_sources:
                continue

            rag_sections.append(
                ContextSection(
                    name=f"rag: {result.section_title}",
                    content=result.content,
                    priority=3,  # Medium priority — between core and nice-to-have
                    source_doc=result.source_document,
                )
            )

        return rag_sections

    def _prioritize_and_trim(self, sections: list[ContextSection], budget: int) -> str:
        """Prioritize sections by importance and trim to budget.

        Priority ordering:
          1. Hard rules (explicit-rules.md)
          2. Core identity (tone, structure, brand)
          3. Platform adaptations, audience
          4. Soft preferences, competitor data
          5. Nice-to-have (vocabulary, trends)
        """
        if not sections:
            return ""

        # Sort by priority (lower = more important)
        sorted_sections = sorted(sections, key=lambda s: s.priority)

        result_parts: list[str] = []
        used_tokens = 0

        for section in sorted_sections:
            section_tokens = section.token_estimate
            if used_tokens + section_tokens <= budget:
                result_parts.append(f"### {section.name}\n{section.content}")
                used_tokens += section_tokens
            else:
                # Try to fit a truncated version
                remaining_budget = budget - used_tokens
                if remaining_budget > 50:  # Only if meaningful space remains
                    # Estimate chars from remaining token budget
                    max_chars = int(remaining_budget * 1.5)  # Conservative for Chinese
                    truncated = section.content[:max_chars]
                    if truncated:
                        result_parts.append(f"### {section.name}\n{truncated}...")
                        used_tokens += _estimate_tokens(truncated)
                break  # Budget exhausted

        return "\n\n".join(result_parts)

    @staticmethod
    def _extract_platform_section(content: str, platform: str) -> str:
        """Extract the section for a specific platform from platform-adaptations.md.

        Looks for a markdown heading matching the platform name.
        """
        # Parse frontmatter inline to avoid circular dependency
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()

        lines = body.split("\n")
        capturing = False
        result_lines: list[str] = []
        platform_lower = platform.lower()

        for line in lines:
            # Check for platform heading (## or ###)
            if line.startswith("#") and platform_lower in line.lower():
                capturing = True
                continue
            elif capturing and line.startswith("#") and platform_lower not in line.lower():
                # Hit the next section
                break
            elif capturing:
                result_lines.append(line)

        return "\n".join(result_lines).strip()
