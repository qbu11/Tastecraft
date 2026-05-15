"""VersionManager — version tracking for content with diff and rollback.

Every generation, user edit, and style adjustment auto-creates a version.
Users can view version history, compare diffs, and rollback (fully or partially).
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.content_version import ContentVersion

logger = logging.getLogger(__name__)


@dataclass
class DiffLine:
    """A single line in a diff output."""

    type: str  # "addition" | "deletion" | "unchanged"
    content: str
    line_number_old: int | None = None
    line_number_new: int | None = None


@dataclass
class VersionDiff:
    """Diff between two content versions."""

    version_from: int
    version_to: int
    title_changed: bool
    body_lines: list[DiffLine]
    additions: int
    deletions: int


class VersionManager:
    """Manage content version history, diffs, and rollbacks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_version(
        self,
        content_id: int,
        title: str,
        body: str,
        platform: str,
        created_by: str = "user_edited",
    ) -> ContentVersion:
        """Save a new version snapshot.

        Auto-increments version_number per content piece.
        """
        # Get next version number
        result = await self.db.execute(
            select(func.coalesce(func.max(ContentVersion.version_number), 0)).where(
                ContentVersion.content_id == content_id
            )
        )
        max_version = result.scalar_one()
        next_version = max_version + 1

        version = ContentVersion(
            content_id=content_id,
            version_number=next_version,
            title=title,
            body=body,
            platform=platform,
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)

        logger.info(
            "Created version %d for content %d (by: %s)",
            next_version,
            content_id,
            created_by,
        )
        return version

    async def get_versions(self, content_id: int) -> list[ContentVersion]:
        """List all versions for a content piece, ordered by version_number."""
        result = await self.db.execute(
            select(ContentVersion)
            .where(ContentVersion.content_id == content_id)
            .order_by(ContentVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self, content_id: int, version_number: int
    ) -> ContentVersion | None:
        """Get a specific version by content_id and version_number."""
        result = await self.db.execute(
            select(ContentVersion).where(
                ContentVersion.content_id == content_id,
                ContentVersion.version_number == version_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_diff(
        self, content_id: int, v1: int, v2: int
    ) -> VersionDiff:
        """Compute diff between two versions.

        Args:
            content_id: The content piece ID.
            v1: Version number of the "from" version.
            v2: Version number of the "to" version.

        Returns:
            VersionDiff with line-by-line changes.
        """
        version_a = await self.get_version(content_id, v1)
        version_b = await self.get_version(content_id, v2)

        if not version_a or not version_b:
            raise ValueError(f"Version(s) not found: v{v1} and/or v{v2}")

        title_changed = version_a.title != version_b.title

        # Compute unified diff on body
        body_a_lines = version_a.body.splitlines(keepends=True)
        body_b_lines = version_b.body.splitlines(keepends=True)

        diff_lines: list[DiffLine] = []
        additions = 0
        deletions = 0

        matcher = difflib.SequenceMatcher(None, body_a_lines, body_b_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k, line in enumerate(body_a_lines[i1:i2]):
                    diff_lines.append(
                        DiffLine(
                            type="unchanged",
                            content=line.rstrip("\n"),
                            line_number_old=i1 + k + 1,
                            line_number_new=j1 + k + 1,
                        )
                    )
            elif tag == "delete":
                for k, line in enumerate(body_a_lines[i1:i2]):
                    diff_lines.append(
                        DiffLine(
                            type="deletion",
                            content=line.rstrip("\n"),
                            line_number_old=i1 + k + 1,
                            line_number_new=None,
                        )
                    )
                    deletions += 1
            elif tag == "insert":
                for k, line in enumerate(body_b_lines[j1:j2]):
                    diff_lines.append(
                        DiffLine(
                            type="addition",
                            content=line.rstrip("\n"),
                            line_number_old=None,
                            line_number_new=j1 + k + 1,
                        )
                    )
                    additions += 1
            elif tag == "replace":
                for k, line in enumerate(body_a_lines[i1:i2]):
                    diff_lines.append(
                        DiffLine(
                            type="deletion",
                            content=line.rstrip("\n"),
                            line_number_old=i1 + k + 1,
                            line_number_new=None,
                        )
                    )
                    deletions += 1
                for k, line in enumerate(body_b_lines[j1:j2]):
                    diff_lines.append(
                        DiffLine(
                            type="addition",
                            content=line.rstrip("\n"),
                            line_number_old=None,
                            line_number_new=j1 + k + 1,
                        )
                    )
                    additions += 1

        return VersionDiff(
            version_from=v1,
            version_to=v2,
            title_changed=title_changed,
            body_lines=diff_lines,
            additions=additions,
            deletions=deletions,
        )

    async def rollback(
        self, content_id: int, target_version: int, user_id: int
    ) -> Content:
        """Rollback content to a specific version (creates a new version).

        This does NOT delete newer versions — it creates a new version
        with the old content, preserving full history.
        """
        target = await self.get_version(content_id, target_version)
        if not target:
            raise ValueError(f"Version {target_version} not found")

        # Fetch the content
        result = await self.db.execute(
            select(Content).where(
                Content.id == content_id,
                Content.user_id == user_id,
            )
        )
        content = result.scalar_one_or_none()
        if not content:
            raise ValueError(f"Content {content_id} not found")

        # Update content to target version's state
        content.title = target.title
        content.body = target.body

        # Create a new version recording the rollback
        await self.create_version(
            content_id=content_id,
            title=target.title,
            body=target.body,
            platform=content.platform,
            created_by="user_edited",
        )

        await self.db.flush()
        await self.db.refresh(content)

        logger.info(
            "Rolled back content %d to version %d", content_id, target_version
        )
        return content

    async def partial_rollback(
        self,
        content_id: int,
        from_version: int,
        sections: list[str],
        user_id: int,
    ) -> Content:
        """Take specific sections from an older version and merge with current.

        Args:
            content_id: The content piece ID.
            from_version: Version to take sections from.
            sections: List of section identifiers (e.g., "opening", "body", "closing").
            user_id: Current user ID for authorization.

        Returns:
            Updated content with merged sections.
        """
        source = await self.get_version(content_id, from_version)
        if not source:
            raise ValueError(f"Version {from_version} not found")

        result = await self.db.execute(
            select(Content).where(
                Content.id == content_id,
                Content.user_id == user_id,
            )
        )
        content = result.scalar_one_or_none()
        if not content:
            raise ValueError(f"Content {content_id} not found")

        # Parse sections from both versions
        source_sections = self._parse_sections(source.body)
        current_sections = self._parse_sections(content.body)

        # Merge: take specified sections from source, keep rest from current
        for section_name in sections:
            if section_name in source_sections:
                current_sections[section_name] = source_sections[section_name]

        # Reconstruct body
        merged_body = self._reconstruct_body(current_sections)

        # Apply title from source if "title" is in sections
        new_title = source.title if "title" in sections else content.title

        content.title = new_title
        content.body = merged_body

        # Create new version for the partial rollback
        await self.create_version(
            content_id=content_id,
            title=new_title,
            body=merged_body,
            platform=content.platform,
            created_by="user_edited",
        )

        await self.db.flush()
        await self.db.refresh(content)

        logger.info(
            "Partial rollback on content %d from version %d (sections: %s)",
            content_id,
            from_version,
            sections,
        )
        return content

    # ── Private Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_sections(body: str) -> dict[str, str]:
        """Parse body into named sections.

        Simple heuristic:
          - "opening": first paragraph (before first blank line or heading)
          - "body": everything in the middle
          - "closing": last paragraph
        """
        if not body.strip():
            return {"opening": "", "body": "", "closing": ""}

        paragraphs = body.strip().split("\n\n")

        if len(paragraphs) <= 1:
            return {"opening": body.strip(), "body": "", "closing": ""}

        if len(paragraphs) == 2:
            return {
                "opening": paragraphs[0].strip(),
                "body": "",
                "closing": paragraphs[1].strip(),
            }

        return {
            "opening": paragraphs[0].strip(),
            "body": "\n\n".join(paragraphs[1:-1]),
            "closing": paragraphs[-1].strip(),
        }

    @staticmethod
    def _reconstruct_body(sections: dict[str, str]) -> str:
        """Reconstruct body from parsed sections."""
        parts = [
            sections.get("opening", ""),
            sections.get("body", ""),
            sections.get("closing", ""),
        ]
        return "\n\n".join(p for p in parts if p)
