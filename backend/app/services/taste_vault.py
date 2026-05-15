"""TasteVault — core vault management service.

Each user+project has an Obsidian-like knowledge base of interconnected markdown
documents storing style, preferences, competitor insights, and lane context.
This vault is NEVER exposed raw to users (it's the moat).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.schemas.vault import VaultHealth

logger = logging.getLogger(__name__)

VAULT_BASE = Path("data/vaults")


class TasteVault:
    """Manages a single user+project vault on the filesystem."""

    def __init__(self, user_id: str, project_slug: str):
        self.user_id = user_id
        self.project_slug = project_slug
        self.root = VAULT_BASE / user_id / project_slug

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    async def initialize(self, onboarding_data: dict) -> None:
        """Create initial vault structure from onboarding results.

        Delegates to VaultInitializer for the actual file creation.
        """
        from app.services.vault_initializer import VaultInitializer

        initializer = VaultInitializer()
        await initializer.create_from_onboarding(
            user_id=self.user_id,
            project_slug=self.project_slug,
            onboarding_data=onboarding_data,
        )

    async def read_document(self, path: str) -> str:
        """Read a vault document by relative path.

        Args:
            path: Relative path within the vault (e.g., "style/tone.md").

        Returns:
            Document content as string, or empty string if not found.
        """
        doc_path = self.root / path
        if not doc_path.exists():
            logger.warning("Vault document not found: %s", doc_path)
            return ""
        return doc_path.read_text(encoding="utf-8")

    async def update_document(self, path: str, content: str) -> None:
        """Update (overwrite) a vault document.

        Args:
            path: Relative path within the vault.
            content: Full new content for the document.
        """
        doc_path = self.root / path
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text(content, encoding="utf-8")
        logger.info("Updated vault document: %s", doc_path)

    async def append_to_document(self, path: str, entry: str) -> None:
        """Append an entry to a vault document (e.g., new edit log entry).

        Args:
            path: Relative path within the vault.
            entry: Text to append (typically a markdown section).
        """
        doc_path = self.root / path
        doc_path.parent.mkdir(parents=True, exist_ok=True)

        existing = ""
        if doc_path.exists():
            existing = doc_path.read_text(encoding="utf-8")

        separator = "\n\n" if existing and not existing.endswith("\n\n") else ""
        doc_path.write_text(existing + separator + entry, encoding="utf-8")
        logger.info("Appended to vault document: %s", doc_path)

    # ── Context Assembly ──────────────────────────────────────────────────────

    async def get_context_for_generation(
        self,
        platform: str,
        topic: str | None = None,
        content_type: str = "post",
    ) -> str:
        """Harness Engineering: assemble the right context for AI generation.

        Delegates to ContextHarness for the actual selection and trimming logic.
        """
        from app.services.context_harness import ContextHarness

        harness = ContextHarness()
        return await harness.assemble_context(
            vault=self,
            platform=platform,
            topic=topic,
            content_type=content_type,
        )

    # ── Update Hooks ──────────────────────────────────────────────────────────

    async def update_from_edit(
        self, edit_data: dict, preference: dict | None = None
    ) -> None:
        """Update vault after a user edit.

        Records the edit in edits-log and optionally updates patterns.

        Args:
            edit_data: Dict with keys: original_text, modified_text, diff_type, platform.
            preference: Optional explicit preference extracted from the edit.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = (
            f"## Edit {timestamp}\n\n"
            f"- **Type**: {edit_data.get('diff_type', 'unknown')}\n"
            f"- **Platform**: {edit_data.get('platform', 'general')}\n"
            f"- **Original**: {edit_data.get('original_text', '')[:200]}\n"
            f"- **Modified**: {edit_data.get('modified_text', '')[:200]}\n"
        )

        if preference:
            log_entry += f"- **Extracted preference**: {preference.get('description', '')}\n"
            log_entry += f"- **Confidence**: {preference.get('confidence', 0.5)}\n"

        await self.append_to_document("preferences/edits-log.md", log_entry)

        if preference and preference.get("confidence", 0) >= 0.7:
            await self._update_patterns(preference)

    async def _update_patterns(self, preference: dict) -> None:
        """Update patterns.md with a high-confidence preference."""
        timestamp = datetime.now(timezone.utc).isoformat()
        pattern_entry = (
            f"\n- [{timestamp}] {preference.get('description', '')} "
            f"(confidence: {preference.get('confidence', 0.5):.2f})\n"
        )
        await self.append_to_document("preferences/patterns.md", pattern_entry)

    async def update_from_competitor(self, competitor_data: dict) -> None:
        """Update vault after competitor monitoring pull.

        Args:
            competitor_data: Dict with keys: account, platform, insights, trends.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = (
            f"## Competitor Update {timestamp}\n\n"
            f"- **Account**: {competitor_data.get('account', 'unknown')}\n"
            f"- **Platform**: {competitor_data.get('platform', 'unknown')}\n"
        )

        insights = competitor_data.get("insights", [])
        if insights:
            entry += "- **Insights**:\n"
            for insight in insights[:10]:
                entry += f"  - {insight}\n"

        trends = competitor_data.get("trends", [])
        if trends:
            entry += "- **Trends**:\n"
            for trend in trends[:5]:
                entry += f"  - {trend}\n"

        await self.append_to_document("competitors/lane-trends.md", entry)

    # ── Health Check ──────────────────────────────────────────────────────────

    async def get_vault_health(self) -> VaultHealth:
        """Check vault completeness and freshness."""
        if not self.root.exists():
            return VaultHealth(
                completeness_pct=0.0,
                last_updated=None,
                document_count=0,
                stale_documents=[],
            )

        expected_docs = [
            "_index.md",
            "style/tone.md",
            "style/structure.md",
            "style/vocabulary.md",
            "style/visual.md",
            "style/platform-adaptations.md",
            "preferences/edits-log.md",
            "preferences/patterns.md",
            "preferences/explicit-rules.md",
            "preferences/conflicts.md",
            "competitors/lane-trends.md",
            "context/brand.md",
            "context/audience.md",
            "context/topics-history.md",
            "evolution/changelog.md",
            "evolution/weekly-digest.md",
        ]

        existing_docs: list[str] = []
        stale_docs: list[str] = []
        latest_mtime: datetime | None = None
        stale_threshold = datetime.now(timezone.utc).timestamp() - (14 * 86400)

        all_md_files = list(self.root.rglob("*.md"))
        document_count = len(all_md_files)

        for doc_rel in expected_docs:
            doc_path = self.root / doc_rel
            if doc_path.exists():
                existing_docs.append(doc_rel)
                mtime = doc_path.stat().st_mtime
                doc_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)

                if latest_mtime is None or doc_dt > latest_mtime:
                    latest_mtime = doc_dt

                if mtime < stale_threshold:
                    stale_docs.append(doc_rel)

        completeness = (len(existing_docs) / len(expected_docs)) * 100 if expected_docs else 0.0

        return VaultHealth(
            completeness_pct=round(completeness, 1),
            last_updated=latest_mtime,
            document_count=document_count,
            stale_documents=stale_docs,
        )

    # ── Utility ───────────────────────────────────────────────────────────────

    def exists(self) -> bool:
        """Check if the vault directory exists."""
        return self.root.exists()

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from a markdown document.

        Returns:
            Tuple of (frontmatter_dict, body_text).
        """
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            frontmatter = {}

        body = parts[2].strip()
        return frontmatter, body
