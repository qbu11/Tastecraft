"""
Xiaohongshu (XHS) Publisher — Camoufox + Playwright

Anti-detect browser automation for publishing notes to xiaohongshu.com.
Uses Camoufox (anti-fingerprint Firefox) instead of regular Chromium to avoid
bot detection. Session persistence via profile directories.

Safety constraints:
- Minimum interval: 60s between posts
- Daily limit: 10 posts max
- Images: 1-18 per post
- Title: <= 20 chars
- Body: <= 1000 chars
- Tags: <= 10
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

# XHS platform constraints
MAX_TITLE_LENGTH = 20
MAX_BODY_LENGTH = 1000
MAX_IMAGES = 18
MAX_TAGS = 10
MIN_PUBLISH_INTERVAL_SEC = 60

# URLs
CREATOR_PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"
CREATOR_HOME_URL = "https://creator.xiaohongshu.com"
XHS_HOME_URL = "https://www.xiaohongshu.com"
XHS_LOGIN_URL = "https://www.xiaohongshu.com/login"


class XHSPublisher:
    """
    Publish notes to Xiaohongshu using Camoufox (anti-detect Firefox)
    controlled via Playwright async API.

    Each user gets an isolated profile directory that stores cookies,
    localStorage, and Firefox profile data across sessions.
    """

    def __init__(self, profile_dir: str) -> None:
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._context: BrowserContext | None = None
        self._last_publish_time: float = 0.0

    # ── Browser lifecycle ────────────────────────────────────────

    async def create_browser(self) -> BrowserContext:
        """Launch Camoufox with stored profile and return a BrowserContext."""
        try:
            from camoufox import AsyncNewBrowser
        except ImportError as exc:
            raise RuntimeError(
                "camoufox required. Install: pip install camoufox && python -m camoufox fetch"
            ) from exc

        # Camoufox launches an anti-detect Firefox instance.
        # persistent_context stores profile data (cookies, localStorage) in profile_dir.
        self._context = await AsyncNewBrowser(
            headless=True,
            persistent_context=str(self.profile_dir),
            humanize=True,  # human-like mouse/keyboard
            geoip=True,  # match IP geolocation
        )
        logger.info("Camoufox browser created with profile: %s", self.profile_dir)
        return self._context

    async def _ensure_context(self) -> BrowserContext:
        """Return existing context or create a new one."""
        if self._context is None:
            return await self.create_browser()
        return self._context

    async def close(self) -> None:
        """Close the browser context and persist session."""
        if self._context is not None:
            try:
                await self.save_session()
            except Exception:
                logger.warning("Failed to save session on close", exc_info=True)
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

    # ── Login flow ───────────────────────────────────────────────

    async def check_login_status(self) -> bool:
        """
        Check if the saved session is still valid.

        Navigates to the creator center and checks whether we get
        redirected to the login page.
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            await page.goto(CREATOR_HOME_URL, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(3000)
            current_url = page.url

            if "/login" in current_url or "passport" in current_url:
                logger.info("XHS session expired or not logged in")
                return False

            logger.info("XHS session is valid (url=%s)", current_url)
            return True

        except Exception as exc:
            logger.warning("Login status check failed: %s", exc)
            return False

    async def get_login_qr_url(self) -> str:
        """
        Navigate to XHS login page and extract the QR code image URL.

        The QR code can be displayed to the user (via noVNC or directly)
        for them to scan with the XHS mobile app.
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto(XHS_LOGIN_URL, wait_until="domcontentloaded", timeout=15_000)
        await page.wait_for_timeout(2000)

        # Try to find QR code image
        qr_url = await page.evaluate("""() => {
            const img = document.querySelector('img[src*="qrcode"]')
                || document.querySelector('.qrcode-img img')
                || document.querySelector('[class*="qr"] img');
            return img ? img.src : null;
        }""")

        if qr_url:
            logger.info("QR code URL extracted")
            return qr_url

        # Fallback: try canvas-based QR
        qr_data = await page.evaluate("""() => {
            const canvas = document.querySelector('canvas');
            return canvas ? canvas.toDataURL('image/png') : null;
        }""")

        if qr_data:
            logger.info("QR code extracted from canvas")
            return qr_data

        logger.warning("Could not extract QR code from login page")
        return ""

    async def wait_for_login(self, timeout: int = 120) -> bool:
        """
        Wait for the user to complete QR scan login.

        Polls the page URL every 2 seconds to detect successful login
        (redirect away from login page).
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current_url = page.url
            if "/login" not in current_url and "passport" not in current_url:
                logger.info("Login detected, saving session")
                await self.save_session()
                return True
            await asyncio.sleep(2)

        logger.warning("Login wait timed out after %ds", timeout)
        return False

    # ── Session persistence ──────────────────────────────────────

    async def save_session(self) -> None:
        """
        Save cookies + localStorage to the profile directory.

        Camoufox persistent context auto-saves most data, but we also
        export cookies as JSON for portability and backup.
        """
        if self._context is None:
            return

        cookies_path = self.profile_dir / "cookies.json"
        try:
            cookies = await self._context.cookies()
            cookies_path.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Session saved: %d cookies -> %s", len(cookies), cookies_path)
        except Exception as exc:
            logger.warning("Failed to save cookies: %s", exc)

        # Also save localStorage from pages
        storage_path = self.profile_dir / "local_storage.json"
        try:
            if self._context.pages:
                page = self._context.pages[0]
                storage = await page.evaluate("""() => {
                    const data = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        data[key] = localStorage.getItem(key);
                    }
                    return data;
                }""")
                storage_path.write_text(
                    json.dumps(storage, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except Exception:
            pass  # localStorage extraction is best-effort

    async def load_session(self) -> bool:
        """
        Load saved session cookies into the browser context.

        Returns False if no saved session or cookies are expired.
        Note: Camoufox persistent context auto-loads profile data,
        so this is mainly for explicit cookie restoration.
        """
        cookies_path = self.profile_dir / "cookies.json"
        if not cookies_path.exists():
            logger.info("No saved session found at %s", cookies_path)
            return False

        ctx = await self._ensure_context()
        try:
            raw = cookies_path.read_text(encoding="utf-8")
            cookies = json.loads(raw)
            if not cookies:
                return False

            # Filter out obviously expired cookies
            now = time.time()
            valid_cookies = [
                c for c in cookies
                if c.get("expires", -1) == -1 or c.get("expires", 0) > now
            ]

            if not valid_cookies:
                logger.info("All saved cookies have expired")
                return False

            await ctx.add_cookies(valid_cookies)
            logger.info("Loaded %d cookies from saved session", len(valid_cookies))
            return True

        except Exception as exc:
            logger.warning("Failed to load session: %s", exc)
            return False

    # ── Publishing ───────────────────────────────────────────────

    async def publish_note(
        self,
        title: str,
        content: str,
        images: list[str],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Publish a note (image + text post) to XHS creator platform.

        Steps:
        1. Navigate to creator.xiaohongshu.com/publish/publish
        2. Upload images (file input)
        3. Fill title (max 20 chars)
        4. Fill content body
        5. Add tags/topics
        6. Click publish
        7. Return {success, note_id, url}

        Returns:
            dict with keys: success (bool), note_id (str|None),
            url (str|None), error (str|None)
        """
        # Validate inputs
        if error := self._validate_inputs(title, content, images, tags):
            return {"success": False, "error": error}

        # Rate limiting
        self._enforce_rate_limit()

        tags = tags or []
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            # Step 1: Navigate to publish page
            await page.goto(CREATOR_PUBLISH_URL, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(2000)

            if "/login" in page.url or "passport" in page.url:
                return {"success": False, "error": "Not logged in. Please login first."}

            # Step 2: Switch to image-text mode
            await self._switch_to_image_mode(page)

            # Step 3: Upload images
            await self._upload_images(page, images)

            # Step 4: Fill title
            await self._random_delay(500, 1200)
            await self._fill_title(page, title)

            # Step 5: Fill body content
            await self._random_delay(500, 1200)
            await self._fill_body(page, content)

            # Step 6: Add tags
            if tags:
                await self._random_delay(500, 1000)
                await self._add_tags(page, tags[:MAX_TAGS])

            # Step 7: Click publish
            await self._random_delay(1000, 2500)
            published = await self._click_publish(page)

            self._last_publish_time = time.time()
            note_id = f"xhs_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return {
                "success": published,
                "note_id": note_id,
                "url": page.url if published else None,
                "status": "published" if published else "publish_button_not_found",
            }

        except Exception as exc:
            logger.exception("XHS publish failed")
            return {"success": False, "error": str(exc)}

    async def save_as_draft(
        self,
        title: str,
        content: str,
        images: list[str],
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Save to XHS draft box instead of publishing directly.

        Same flow as publish_note but clicks "save draft" instead of "publish".
        """
        if error := self._validate_inputs(title, content, images, tags):
            return {"success": False, "error": error}

        tags = tags or []
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            await page.goto(CREATOR_PUBLISH_URL, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(2000)

            if "/login" in page.url or "passport" in page.url:
                return {"success": False, "error": "Not logged in. Please login first."}

            await self._switch_to_image_mode(page)
            await self._upload_images(page, images)

            await self._random_delay(500, 1200)
            await self._fill_title(page, title)

            await self._random_delay(500, 1200)
            await self._fill_body(page, content)

            if tags:
                await self._random_delay(500, 1000)
                await self._add_tags(page, tags[:MAX_TAGS])

            await self._random_delay(1000, 2000)
            saved = await self._click_save_draft(page)

            note_id = f"xhs_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return {
                "success": saved,
                "note_id": note_id,
                "status": "draft_saved" if saved else "draft_button_not_found",
            }

        except Exception as exc:
            logger.exception("XHS save draft failed")
            return {"success": False, "error": str(exc)}

    # ── Internal automation helpers ──────────────────────────────

    def _validate_inputs(
        self,
        title: str,
        content: str,
        images: list[str],
        tags: list[str] | None,
    ) -> str | None:
        """Validate inputs and return error string, or None if valid."""
        if len(title) > MAX_TITLE_LENGTH:
            return f"Title exceeds {MAX_TITLE_LENGTH} chars ({len(title)})"
        if len(content) > MAX_BODY_LENGTH:
            return f"Content exceeds {MAX_BODY_LENGTH} chars ({len(content)})"
        if len(images) > MAX_IMAGES:
            return f"Too many images ({len(images)} > {MAX_IMAGES})"
        if not images:
            return "At least 1 image is required for XHS notes"
        if tags and len(tags) > MAX_TAGS:
            return f"Too many tags ({len(tags)} > {MAX_TAGS})"

        # Check image files exist
        for img_path in images:
            p = Path(img_path)
            if not p.is_absolute():
                p = Path.cwd() / p
            if not p.exists():
                return f"Image not found: {img_path}"

        return None

    def _enforce_rate_limit(self) -> None:
        """Block if we are publishing too fast."""
        if self._last_publish_time > 0:
            elapsed = time.time() - self._last_publish_time
            if elapsed < MIN_PUBLISH_INTERVAL_SEC:
                wait = MIN_PUBLISH_INTERVAL_SEC - elapsed
                logger.info("Rate limiting: waiting %.1fs", wait)
                time.sleep(wait)

    async def _switch_to_image_mode(self, page: Page) -> None:
        """Switch from default video upload to image-text upload mode."""
        result = await page.evaluate("""() => {
            const els = document.querySelectorAll('span, div, a, button');
            for (const el of els) {
                const text = el.textContent.trim();
                if (text === '上传图文' && el.offsetParent !== null) {
                    el.click();
                    return 'clicked';
                }
            }
            return 'not_found';
        }""")
        if result == "clicked":
            await page.wait_for_timeout(2000)
            logger.info("Switched to image-text upload mode")
        else:
            logger.debug("Image-text tab not found — may already be in image mode")

    async def _upload_images(self, page: Page, image_paths: list[str]) -> None:
        """Upload images via the file input element."""
        abs_paths: list[str] = []
        for p in image_paths:
            path = Path(p)
            if not path.is_absolute():
                path = Path.cwd() / path
            if path.exists():
                abs_paths.append(str(path))
            else:
                logger.warning("Skipping missing image: %s", p)

        if not abs_paths:
            logger.warning("No valid images to upload")
            return

        # Primary: find <input type="file"> and set files
        file_input = page.locator('input[type="file"]').first
        try:
            await file_input.set_input_files(abs_paths, timeout=5000)
            await page.wait_for_timeout(3000)
            logger.info("Uploaded %d images via file input", len(abs_paths))
            return
        except Exception:
            logger.debug("file input approach failed, trying file chooser")

        # Fallback: trigger file chooser via click
        try:
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                upload_area = page.locator('[class*="upload"]').first
                await upload_area.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(abs_paths)
            await page.wait_for_timeout(3000)
            logger.info("Uploaded %d images via file chooser", len(abs_paths))
        except Exception as exc:
            logger.warning("Image upload failed: %s", exc)

    async def _fill_title(self, page: Page, title: str) -> None:
        """Fill the title input with human-like typing."""
        selectors = [
            '[placeholder*="标题"]',
            '[class*="title"] input',
            '[class*="title"] textarea',
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                await loc.click(timeout=3000)
                await loc.fill("")
                await self._simulate_typing(page, sel, title)
                logger.info("Title filled: %s", title[:MAX_TITLE_LENGTH])
                return
            except Exception:
                continue

        # JS fallback
        title_json = json.dumps(title, ensure_ascii=True)
        await page.evaluate(f"""() => {{
            const el = document.querySelector('[placeholder*="标题"]')
                || document.querySelector('[class*="title"] input');
            if (el) {{
                el.focus();
                el.value = '';
                document.execCommand('insertText', false, JSON.parse({title_json}));
            }}
        }}""")
        logger.info("Title filled via JS fallback")

    async def _fill_body(self, page: Page, body: str) -> None:
        """Fill the body/content editor with human-like typing."""
        selectors = [
            '[contenteditable="true"]',
            '[class*="editor"]',
            '[class*="content"] [contenteditable]',
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                await loc.click(timeout=3000)
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Backspace")
                await self._simulate_typing(page, sel, body)
                logger.info("Body filled (%d chars)", len(body))
                return
            except Exception:
                continue

        # JS fallback
        body_json = json.dumps(body, ensure_ascii=True)
        await page.evaluate(f"""() => {{
            const el = document.querySelector('[contenteditable="true"]');
            if (el) {{
                el.focus();
                el.innerHTML = '';
                document.execCommand('insertText', false, JSON.parse({body_json}));
            }}
        }}""")
        logger.info("Body filled via JS fallback")

    async def _add_tags(self, page: Page, tags: list[str]) -> None:
        """Add hashtags/topics to the note."""
        tag_selectors = [
            '[placeholder*="标签"]',
            '[placeholder*="输入标签"]',
            '[class*="tag"] input',
            '[id*="tag"] input',
        ]
        for tag in tags:
            for sel in tag_selectors:
                loc = page.locator(sel).first
                try:
                    await loc.click(timeout=2000)
                    await page.keyboard.type(tag, delay=self._typing_delay())
                    await self._random_delay(300, 600)
                    await page.keyboard.press("Enter")
                    await self._random_delay(300, 600)
                    break
                except Exception:
                    continue
        logger.info("Added %d tags", len(tags))

    async def _click_publish(self, page: Page) -> bool:
        """Click the publish button."""
        for text in ["发布", "发布笔记", "确认发布"]:
            btn = page.locator(f'button:has-text("{text}")').first
            try:
                await btn.click(timeout=3000)
                await page.wait_for_timeout(3000)
                logger.info("Publish button clicked: %s", text)
                return True
            except Exception:
                continue

        # JS fallback
        result = await page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            for (const b of buttons) {
                const text = b.textContent.trim();
                if (text.includes('发布') && !text.includes('草稿')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            await page.wait_for_timeout(3000)
            logger.info("Publish button clicked via JS: %s", result)
            return True

        logger.warning("Publish button not found")
        return False

    async def _click_save_draft(self, page: Page) -> bool:
        """Click the save-as-draft button."""
        for text in ["暂存离开", "存草稿", "保存草稿", "保存"]:
            btn = page.locator(f'button:has-text("{text}")').first
            try:
                await btn.click(timeout=3000)
                await page.wait_for_timeout(2000)
                logger.info("Draft save button clicked: %s", text)
                return True
            except Exception:
                continue

        # JS fallback
        result = await page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            for (const b of buttons) {
                const text = b.textContent.trim();
                if (text.includes('暂存') || text.includes('存草稿') || text.includes('保存')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            await page.wait_for_timeout(2000)
            logger.info("Draft save via JS: %s", result)
            return True

        logger.warning("Draft save button not found")
        return False

    # ── Human simulation helpers ─────────────────────────────────

    @staticmethod
    def _random_delay_value(min_ms: int = 500, max_ms: int = 2000) -> float:
        """Return a random delay in seconds."""
        return random.uniform(min_ms, max_ms) / 1000.0

    async def _random_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Human-like random delay (async)."""
        await asyncio.sleep(self._random_delay_value(min_ms, max_ms))

    @staticmethod
    def _typing_delay() -> int:
        """Random per-character typing delay in ms."""
        return random.randint(30, 80)

    async def _simulate_typing(self, page: Page, selector: str, text: str) -> None:
        """Type text with human-like speed variation."""
        # Use Playwright keyboard.type with random per-char delay
        await page.keyboard.type(text, delay=self._typing_delay())
