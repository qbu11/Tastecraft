"""Competitor Monitoring — sync posts, detect viral content, extract trends."""

import logging
from datetime import datetime, timezone

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.competitor import Competitor
from app.models.competitor_post import CompetitorPost
from app.schemas.competitor import SyncResult, TrendReport, TrendingTopic, ViralAlert

logger = logging.getLogger(__name__)

# Lazy-init TikHub client
_tikhub_client = None


def _get_tikhub():
    """Get or create TikHub client (lazy singleton)."""
    global _tikhub_client
    if _tikhub_client is None:
        try:
            from tikhub import Client as TikHubClient

            _tikhub_client = TikHubClient(api_key=settings.tikhub_api_key)
        except ImportError:
            logger.warning("tikhub SDK not installed — competitor sync unavailable")
            raise
    return _tikhub_client


# ── Platform fetch adapters ──


async def _fetch_xiaohongshu_posts(account_id: str, since: datetime | None) -> list[dict]:
    """Fetch XHS notes for a user via TikHub."""
    client = _get_tikhub()
    try:
        result = await client.xiaohongshu_web.get_user_notes_v2(user_id=account_id)
        notes = result.get("notes", result.get("data", {}).get("notes", []))
        if not isinstance(notes, list):
            notes = []
        posts = []
        for note in notes:
            published_at = note.get("time") or note.get("create_time")
            if since and published_at and published_at < since.timestamp():
                continue
            posts.append({
                "platform_post_id": note.get("note_id", note.get("id", "")),
                "title": note.get("title", ""),
                "content_text": note.get("desc", ""),
                "media_urls": note.get("image_list", []),
                "tags": [t.get("name", "") for t in note.get("tag_list", [])],
                "likes": note.get("liked_count", 0),
                "comments": note.get("comment_count", 0),
                "shares": note.get("share_count", 0),
                "views": note.get("view_count", 0),
                "published_at": (
                    datetime.fromtimestamp(published_at, tz=timezone.utc)
                    if published_at
                    else None
                ),
            })
        return posts
    except Exception as exc:
        logger.error("XHS fetch failed for %s: %s", account_id, exc)
        raise


async def _fetch_weibo_posts(account_id: str, since: datetime | None) -> list[dict]:
    """Fetch Weibo posts for a user via TikHub."""
    client = _get_tikhub()
    try:
        params = {"uid": account_id}
        if since:
            params["since_id"] = ""
        result = await client.weibo_web.fetch_user_posts(**params)
        statuses = result.get("statuses", result.get("data", {}).get("statuses", []))
        if not isinstance(statuses, list):
            statuses = []
        posts = []
        for status in statuses:
            posts.append({
                "platform_post_id": str(status.get("id", "")),
                "title": "",
                "content_text": status.get("text_raw", status.get("text", "")),
                "media_urls": [
                    pic.get("large", {}).get("url", "")
                    for pic in status.get("pic_infos", {}).values()
                ],
                "tags": [t.get("tag_name", "") for t in status.get("tag_struct", [])],
                "likes": status.get("attitudes_count", 0),
                "comments": status.get("comments_count", 0),
                "shares": status.get("reposts_count", 0),
                "views": 0,
                "published_at": None,
            })
        return posts
    except Exception as exc:
        logger.error("Weibo fetch failed for %s: %s", account_id, exc)
        raise


async def _fetch_zhihu_posts(account_id: str, since: datetime | None) -> list[dict]:
    """Fetch Zhihu articles for a user via TikHub."""
    client = _get_tikhub()
    try:
        result = await client.zhihu_web.fetch_user_articles(user_url_token=account_id)
        articles = result.get("data", [])
        if not isinstance(articles, list):
            articles = []
        posts = []
        for article in articles:
            posts.append({
                "platform_post_id": str(article.get("id", "")),
                "title": article.get("title", ""),
                "content_text": article.get("excerpt", ""),
                "media_urls": [],
                "tags": [t.get("name", "") for t in article.get("topics", [])],
                "likes": article.get("voteup_count", 0),
                "comments": article.get("comment_count", 0),
                "shares": 0,
                "views": 0,
                "published_at": None,
            })
        return posts
    except Exception as exc:
        logger.error("Zhihu fetch failed for %s: %s", account_id, exc)
        raise


async def _fetch_douyin_posts(account_id: str, since: datetime | None) -> list[dict]:
    """Fetch Douyin videos for a user via TikHub."""
    client = _get_tikhub()
    try:
        result = await client.douyin_web.fetch_user_post_videos(sec_user_id=account_id)
        videos = result.get("aweme_list", result.get("data", {}).get("aweme_list", []))
        if not isinstance(videos, list):
            videos = []
        posts = []
        for video in videos:
            stats = video.get("statistics", {})
            posts.append({
                "platform_post_id": str(video.get("aweme_id", "")),
                "title": video.get("desc", ""),
                "content_text": video.get("desc", ""),
                "media_urls": [video.get("video", {}).get("cover", {}).get("url_list", [""])[0]],
                "tags": [t.get("hashtag_name", "") for t in video.get("text_extra", [])],
                "likes": stats.get("digg_count", 0),
                "comments": stats.get("comment_count", 0),
                "shares": stats.get("share_count", 0),
                "views": stats.get("play_count", 0),
                "published_at": (
                    datetime.fromtimestamp(video.get("create_time", 0), tz=timezone.utc)
                    if video.get("create_time")
                    else None
                ),
            })
        return posts
    except Exception as exc:
        logger.error("Douyin fetch failed for %s: %s", account_id, exc)
        raise


async def _fetch_wechat_posts(account_name: str, since: datetime | None) -> list[dict]:
    """Fetch WeChat articles by keyword search (limited coverage)."""
    client = _get_tikhub()
    try:
        result = await client.wechat_media_platform_web.fetch_search_article(
            keyword=account_name
        )
        articles = result.get("articles", result.get("data", {}).get("articles", []))
        if not isinstance(articles, list):
            articles = []
        posts = []
        for article in articles:
            posts.append({
                "platform_post_id": article.get("url", str(article.get("id", ""))),
                "title": article.get("title", ""),
                "content_text": article.get("abstract", ""),
                "media_urls": [],
                "tags": [],
                "likes": article.get("read_count", 0),
                "comments": 0,
                "shares": 0,
                "views": article.get("read_count", 0),
                "published_at": None,
            })
        return posts
    except Exception as exc:
        logger.error("WeChat fetch failed for %s: %s", account_name, exc)
        raise


_PLATFORM_FETCHERS = {
    "xiaohongshu": _fetch_xiaohongshu_posts,
    "weibo": _fetch_weibo_posts,
    "zhihu": _fetch_zhihu_posts,
    "douyin": _fetch_douyin_posts,
    "wechat": _fetch_wechat_posts,
}


# ── Core service ──


class CompetitorTracker:
    """Service for syncing competitor accounts and analyzing trends."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_competitor(self, competitor_id: int) -> SyncResult:
        """Fetch new posts from a competitor account since last sync."""
        result = await self.db.execute(
            select(Competitor).where(Competitor.id == competitor_id)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            return SyncResult(
                competitor_id=competitor_id,
                competitor_name="unknown",
                platform="unknown",
                error="Competitor not found",
            )

        fetcher = _PLATFORM_FETCHERS.get(competitor.platform)
        if not fetcher:
            return SyncResult(
                competitor_id=competitor.id,
                competitor_name=competitor.account_name,
                platform=competitor.platform,
                error=f"Unsupported platform: {competitor.platform}",
            )

        try:
            # For WeChat, use account_name as search keyword
            fetch_key = (
                competitor.account_name
                if competitor.platform == "wechat"
                else competitor.account_id
            )
            raw_posts = await fetcher(fetch_key, competitor.last_synced_at)
        except Exception as exc:
            return SyncResult(
                competitor_id=competitor.id,
                competitor_name=competitor.account_name,
                platform=competitor.platform,
                error=str(exc),
            )

        new_count = 0
        updated_count = 0
        viral_count = 0

        # Compute average engagement for viral detection
        avg_engagement = await self._get_avg_engagement(competitor.id)

        for post_data in raw_posts:
            existing = await self.db.execute(
                select(CompetitorPost).where(
                    CompetitorPost.competitor_id == competitor.id,
                    CompetitorPost.platform_post_id == post_data["platform_post_id"],
                )
            )
            existing_post = existing.scalar_one_or_none()

            engagement = (
                post_data.get("likes", 0)
                + post_data.get("comments", 0)
                + post_data.get("shares", 0)
            )
            is_viral = avg_engagement > 0 and engagement > 3 * avg_engagement

            if existing_post:
                # Update engagement metrics
                existing_post.likes = post_data.get("likes", 0)
                existing_post.comments = post_data.get("comments", 0)
                existing_post.shares = post_data.get("shares", 0)
                existing_post.views = post_data.get("views", 0)
                existing_post.is_viral = is_viral
                existing_post.fetched_at = datetime.now(timezone.utc)
                updated_count += 1
            else:
                new_post = CompetitorPost(
                    competitor_id=competitor.id,
                    platform_post_id=post_data["platform_post_id"],
                    title=post_data.get("title"),
                    content_text=post_data.get("content_text"),
                    media_urls=post_data.get("media_urls"),
                    tags=post_data.get("tags"),
                    likes=post_data.get("likes", 0),
                    comments=post_data.get("comments", 0),
                    shares=post_data.get("shares", 0),
                    views=post_data.get("views", 0),
                    published_at=post_data.get("published_at"),
                    fetched_at=datetime.now(timezone.utc),
                    is_viral=is_viral,
                )
                self.db.add(new_post)
                new_count += 1

            if is_viral:
                viral_count += 1

        # Update competitor metadata
        competitor.last_synced_at = datetime.now(timezone.utc)
        competitor.total_posts_tracked += new_count
        await self.db.flush()

        return SyncResult(
            competitor_id=competitor.id,
            competitor_name=competitor.account_name,
            platform=competitor.platform,
            new_posts=new_count,
            updated_posts=updated_count,
            viral_detected=viral_count,
        )

    async def sync_all_for_user(self, user_id: int) -> list[SyncResult]:
        """Sync all competitors for a user."""
        result = await self.db.execute(
            select(Competitor).where(Competitor.user_id == user_id)
        )
        competitors = result.scalars().all()

        results = []
        for competitor in competitors:
            sync_result = await self.sync_competitor(competitor.id)
            results.append(sync_result)

        return results

    async def analyze_trends(
        self, user_id: int, project_id: int | None = None, period_days: int = 7
    ) -> TrendReport:
        """Analyze competitor posts to extract lane trends."""
        # Gather recent posts
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        query = (
            select(CompetitorPost)
            .join(Competitor)
            .where(
                Competitor.user_id == user_id,
                CompetitorPost.fetched_at >= cutoff,
            )
        )
        if project_id:
            query = query.where(Competitor.project_id == project_id)

        result = await self.db.execute(query)
        posts = list(result.scalars().all())

        if not posts:
            return TrendReport(
                project_id=project_id,
                generated_at=datetime.now(timezone.utc),
                period_days=period_days,
                summary="No competitor posts found in the analysis period.",
            )

        # Extract topics via Claude
        topics = await self.extract_topics(posts)

        # Detect viral posts
        viral_alerts = await self._build_viral_alerts(posts)

        # Build topic frequency map
        topic_stats = self._aggregate_topic_stats(posts, topics)

        # Generate summary via Claude
        summary = await self._generate_trend_summary(topic_stats, viral_alerts, period_days)

        return TrendReport(
            project_id=project_id,
            generated_at=datetime.now(timezone.utc),
            period_days=period_days,
            top_topics=topic_stats[:10],
            viral_posts=viral_alerts[:10],
            total_posts_analyzed=len(posts),
            summary=summary,
        )

    async def detect_viral(self, competitor_id: int) -> list[CompetitorPost]:
        """Identify viral posts (3x+ average engagement)."""
        result = await self.db.execute(
            select(CompetitorPost).where(
                CompetitorPost.competitor_id == competitor_id,
                CompetitorPost.is_viral.is_(True),
            )
        )
        return list(result.scalars().all())

    async def extract_topics(self, posts: list[CompetitorPost]) -> list[str]:
        """Use Claude to extract trending topics from recent posts."""
        if not posts:
            return []

        # Build a compact summary of post titles/content for analysis
        post_summaries = []
        for post in posts[:50]:  # Limit to avoid token overflow
            title = post.title or ""
            content = (post.content_text or "")[:200]
            tags = ", ".join(post.tags) if isinstance(post.tags, list) else ""
            post_summaries.append(f"- {title}: {content} [tags: {tags}]")

        posts_text = "\n".join(post_summaries)

        try:
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Analyze these competitor social media posts and extract the top "
                            "trending topics. Return ONLY a JSON array of topic strings, "
                            "ordered by relevance. Maximum 15 topics.\n\n"
                            f"Posts:\n{posts_text}"
                        ),
                    }
                ],
            )
            import json

            text = response.content[0].text.strip()
            # Handle markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception as exc:
            logger.warning("Topic extraction via Claude failed: %s", exc)
            # Fallback: extract from tags
            tag_counts: dict[str, int] = {}
            for post in posts:
                if isinstance(post.tags, list):
                    for tag in post.tags:
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
            return [tag for tag, _ in sorted_tags[:15]]

    async def update_vault_trends(
        self, user_id: int, project_slug: str, trends: TrendReport
    ) -> None:
        """Update the Taste Vault lane-trends.md with new findings."""
        from app.services.taste_vault import TasteVault

        vault = TasteVault()
        trends_md = f"# Lane Trends — {trends.generated_at.strftime('%Y-%m-%d')}\n\n"
        trends_md += f"Period: {trends.period_days} days | Posts analyzed: {trends.total_posts_analyzed}\n\n"

        if trends.top_topics:
            trends_md += "## Trending Topics\n\n"
            for topic in trends.top_topics:
                trends_md += (
                    f"- **{topic.topic}** — {topic.frequency} mentions, "
                    f"avg engagement {topic.avg_engagement:.0f}\n"
                )
            trends_md += "\n"

        if trends.viral_posts:
            trends_md += "## Viral Posts\n\n"
            for vp in trends.viral_posts:
                trends_md += (
                    f"- [{vp.platform}] {vp.title or 'Untitled'} by {vp.competitor_name} — "
                    f"{vp.likes} likes, {vp.engagement_ratio:.1f}x avg\n"
                )
            trends_md += "\n"

        if trends.summary:
            trends_md += f"## Summary\n\n{trends.summary}\n"

        try:
            await vault.write_file(user_id, project_slug, "lane-trends.md", trends_md)
        except Exception as exc:
            logger.warning("Failed to update vault trends: %s", exc)

    # ── Private helpers ──

    async def _get_avg_engagement(self, competitor_id: int) -> float:
        """Get average engagement (likes+comments+shares) for a competitor."""
        result = await self.db.execute(
            select(
                func.avg(
                    CompetitorPost.likes
                    + CompetitorPost.comments
                    + CompetitorPost.shares
                )
            ).where(CompetitorPost.competitor_id == competitor_id)
        )
        avg = result.scalar_one_or_none()
        return float(avg) if avg else 0.0

    async def _build_viral_alerts(
        self, posts: list[CompetitorPost]
    ) -> list[ViralAlert]:
        """Build viral alerts from posts marked as viral."""
        alerts = []
        for post in posts:
            if not post.is_viral:
                continue

            # Look up competitor name
            comp_result = await self.db.execute(
                select(Competitor).where(Competitor.id == post.competitor_id)
            )
            competitor = comp_result.scalar_one_or_none()

            avg = await self._get_avg_engagement(post.competitor_id)
            engagement = post.likes + post.comments + post.shares
            ratio = engagement / avg if avg > 0 else 0.0

            alerts.append(
                ViralAlert(
                    post_id=post.id,
                    competitor_name=competitor.account_name if competitor else "Unknown",
                    platform=competitor.platform if competitor else "unknown",
                    title=post.title,
                    likes=post.likes,
                    comments=post.comments,
                    shares=post.shares,
                    views=post.views,
                    published_at=post.published_at,
                    engagement_ratio=ratio,
                )
            )

        # Sort by engagement ratio descending
        alerts.sort(key=lambda a: a.engagement_ratio, reverse=True)
        return alerts

    def _aggregate_topic_stats(
        self, posts: list[CompetitorPost], extracted_topics: list[str]
    ) -> list[TrendingTopic]:
        """Count topic frequency and engagement from posts."""
        topic_data: dict[str, dict] = {}

        for topic in extracted_topics:
            topic_lower = topic.lower()
            for post in posts:
                title = (post.title or "").lower()
                content = (post.content_text or "").lower()
                tags_text = " ".join(post.tags).lower() if isinstance(post.tags, list) else ""

                if topic_lower in title or topic_lower in content or topic_lower in tags_text:
                    if topic not in topic_data:
                        topic_data[topic] = {
                            "frequency": 0,
                            "total_engagement": 0,
                            "titles": [],
                        }
                    topic_data[topic]["frequency"] += 1
                    topic_data[topic]["total_engagement"] += (
                        post.likes + post.comments + post.shares
                    )
                    if post.title and len(topic_data[topic]["titles"]) < 3:
                        topic_data[topic]["titles"].append(post.title)

        result = []
        for topic, data in topic_data.items():
            if data["frequency"] > 0:
                result.append(
                    TrendingTopic(
                        topic=topic,
                        frequency=data["frequency"],
                        avg_engagement=data["total_engagement"] / data["frequency"],
                        example_titles=data["titles"],
                    )
                )

        result.sort(key=lambda t: t.frequency, reverse=True)
        return result

    async def _generate_trend_summary(
        self,
        topics: list[TrendingTopic],
        viral: list[ViralAlert],
        period_days: int,
    ) -> str:
        """Generate a human-readable trend summary via Claude."""
        if not topics and not viral:
            return "No significant trends detected in this period."

        context_parts = [f"Analysis period: last {period_days} days\n"]

        if topics:
            context_parts.append("Top topics:")
            for t in topics[:5]:
                context_parts.append(
                    f"  - {t.topic}: {t.frequency} mentions, "
                    f"avg engagement {t.avg_engagement:.0f}"
                )

        if viral:
            context_parts.append("\nViral content:")
            for v in viral[:3]:
                context_parts.append(
                    f"  - [{v.platform}] {v.title or 'Untitled'}: "
                    f"{v.engagement_ratio:.1f}x average engagement"
                )

        context = "\n".join(context_parts)

        try:
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Based on this competitor analysis data, write a brief "
                            "(2-3 sentences) trend summary in Chinese. Focus on actionable "
                            "insights for content creators.\n\n"
                            f"{context}"
                        ),
                    }
                ],
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning("Trend summary generation failed: %s", exc)
            return f"Analyzed {len(topics)} trending topics and {len(viral)} viral posts."
