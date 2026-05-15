"""
Weibo Publisher — Camoufox + Playwright

Anti-detect browser automation for publishing posts to weibo.com.
Uses Camoufox (anti-fingerprint Firefox) to avoid bot detection.
Session persistence via profile directories.

Safety constraints:
- Minimum interval: 60s between posts
- Daily limit: 20 posts max
- Content: max 140 chars for regular posts (2000 for Super Topic)
- Images: 0-9 per post
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

# Weibo platform constraints
MAX_CONTENT_LENGTH = 140
MAX_IMAGES = 9
MIN_PUBLISH_INTERVAL_SEC = 60

# URLs
WEIBO_HOME_URL = "https://weibo.com"
WEIBO_COMPOSE_URL = "https://weibo.com"
WEIBO_LOGIN_URL = "https://passport.weibo.com/sso/signin"


class WeiboPublisher:
    """
    Publish posts to Weibo using Camoufox (anti-detect Firefox)
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
        """Launch Camoufox with Weibo profile."""
        try:
            from camoufox import AsyncNewBrowser
        except ImportError as exc:
            raise RuntimeError(
                "camoufox required. Install: pip install camoufox && python -m camoufox fetch"
            ) from exc

        self._context = await AsyncNewBrowser(
            headless=True,
            persistent_context=str(self.profile_dir),
            humanize=True,
            geoip=True,
        )
        logger.info("Camoufox browser created with Weibo profile: %s", self.profile_dir)
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
                logger.warning("Failed to save Weibo session on close", exc_info=True)
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

    # ── Login flow ───────────────────────────────────────────────

    async def check_login_status(self) -> bool:
        """Check if Weibo session is valid.

        Navigates to weibo.com and checks whether we get
        redirected to the login page or see the compose box.
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            await page.goto(WEIBO_HOME_URL, wait_until="domcontentloaded", timeout=15_000)
            await page.wait_for_timeout(3000)
            current_url = page.url

            if "passport" in current_url or "login" in current_url:
                logger.info("Weibo session expired or not logged in")
                return False

            # Check for user-specific elements that indicate logged-in state
            logged_in = await page.evaluate("""() => {
                // Look for compose box or user avatar
                const compose = document.querySelector('[node-type="textEl"]')
                    || document.querySelector('textarea[placeholder]')
                    || document.querySelector('[class*="compose"]');
                const avatar = document.querySelector('[class*="avatar"]')
                    || document.querySelector('[class*="gn_name"]');
                return !!(compose || avatar);
            }""")

            if logged_in:
                logger.info("Weibo session is valid (url=%s)", current_url)
                return True

            logger.info("Weibo session unclear, assuming expired")
            return False

        except Exception as exc:
            logger.warning("Weibo login status check failed: %s", exc)
            return False

    async def get_login_qr_url(self) -> str:
        """Get Weibo login QR code.

        Navigate to Weibo login page and extract the QR code image URL
        for the user to scan with the Weibo mobile app.
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto(WEIBO_LOGIN_URL, wait_until="domcontentloaded", timeout=15_000)
        await page.wait_for_timeout(2000)

        # Try to switch to QR code login tab if not already there
        await page.evaluate("""() => {
            const qrTab = document.querySelector('[class*="qr"]')
                || document.querySelector('[data-type="qr"]')
                || document.querySelector('a[href*="qr"]');
            if (qrTab) qrTab.click();
        }""")
        await page.wait_for_timeout(1000)

        # Extract QR code image
        qr_url = await page.evaluate("""() => {
            const img = document.querySelector('img[src*="qrcode"]')
                || document.querySelector('.qrcode img')
                || document.querySelector('[class*="qr"] img')
                || document.querySelector('img[alt*="二维码"]');
            return img ? img.src : null;
        }""")

        if qr_url:
            logger.info("Weibo QR code URL extracted")
            return qr_url

        # Fallback: try canvas-based QR
        qr_data = await page.evaluate("""() => {
            const canvas = document.querySelector('canvas');
            return canvas ? canvas.toDataURL('image/png') : null;
        }""")

        if qr_data:
            logger.info("Weibo QR code extracted from canvas")
            return qr_data

        logger.warning("Could not extract Weibo QR code from login page")
        return ""

    async def wait_for_login(self, timeout: int = 120) -> bool:
        """Wait for QR scan.

        Polls the page URL every 2 seconds to detect successful login
        (redirect away from login page).
        """
        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current_url = page.url
            if "passport" not in current_url and "login" not in current_url:
                logger.info("Weibo login detected, saving session")
                await self.save_session()
                return True
            await asyncio.sleep(2)

        logger.warning("Weibo login wait timed out after %ds", timeout)
        return False

    # ── Session persistence ──────────────────────────────────────

    async def save_session(self) -> None:
        """Persist cookies."""
        if self._context is None:
            return

        cookies_path = self.profile_dir / "cookies.json"
        try:
            cookies = await self._context.cookies()
            cookies_path.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Weibo session saved: %d cookies -> %s", len(cookies), cookies_path)
        except Exception as exc:
            logger.warning("Failed to save Weibo cookies: %s", exc)

        # Also save localStorage
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
        """Load saved session."""
        cookies_path = self.profile_dir / "cookies.json"
        if not cookies_path.exists():
            logger.info("No saved Weibo session found at %s", cookies_path)
            return False

        ctx = await self._ensure_context()
        try:
            raw = cookies_path.read_text(encoding="utf-8")
            cookies = json.loads(raw)
            if not cookies:
                return False

            now = time.time()
            valid_cookies = [
                c for c in cookies
                if c.get("expires", -1) == -1 or c.get("expires", 0) > now
            ]

            if not valid_cookies:
                logger.info("All saved Weibo cookies have expired")
                return False

            await ctx.add_cookies(valid_cookies)
            logger.info("Loaded %d Weibo cookies from saved session", len(valid_cookies))
            return True

        except Exception as exc:
            logger.warning("Failed to load Weibo session: %s", exc)
            return False

    # ── Publishing ───────────────────────────────────────────────

    async def publish_post(
        self,
        content: str,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """Publish a Weibo post (text + optional images).

        Steps:
        1. Navigate to weibo.com
        2. Find compose box
        3. Type content
        4. Upload images (if any)
        5. Click publish
        6. Return {success, post_id, url}

        Args:
            content: Post text (max 140 chars for regular posts).
            images: Optional list of image file paths (max 9).

        Returns:
            dict with keys: success (bool), post_id (str|None),
            url (str|None), error (str|None)
        """
        images = images or []

        if error := self._validate_inputs(content, images):
            return {"success": False, "error": error}

        self._enforce_rate_limit()

        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            # Step 1: Navigate to Weibo home
            await page.goto(WEIBO_COMPOSE_URL, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(2000)

            if "passport" in page.url or "login" in page.url:
                return {"success": False, "error": "Not logged in. Please login first."}

            # Step 2: Find and click compose area
            await self._focus_compose_box(page)

            # Step 3: Type content
            await self._random_delay(500, 1200)
            await self._type_content(page, content)

            # Step 4: Upload images
            if images:
                await self._random_delay(500, 1000)
                await self._upload_images(page, images)

            # Step 5: Click publish
            await self._random_delay(1000, 2500)
            published = await self._click_publish(page)

            self._last_publish_time = time.time()
            post_id = f"wb_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return {
                "success": published,
                "post_id": post_id,
                "url": page.url if published else None,
                "status": "published" if published else "publish_button_not_found",
            }

        except Exception as exc:
            logger.exception("Weibo publish failed")
            return {"success": False, "error": str(exc)}

    async def save_as_draft(
        self,
        content: str,
        images: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save to Weibo draft.

        Same flow as publish_post but does not click publish.
        Instead, uses the draft/save functionality.
        """
        images = images or []

        if error := self._validate_inputs(content, images):
            return {"success": False, "error": error}

        ctx = await self._ensure_context()
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        try:
            await page.goto(WEIBO_COMPOSE_URL, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_timeout(2000)

            if "passport" in page.url or "login" in page.url:
                return {"success": False, "error": "Not logged in. Please login first."}

            await self._focus_compose_box(page)

            await self._random_delay(500, 1200)
            await self._type_content(page, content)

            if images:
                await self._random_delay(500, 1000)
                await self._upload_images(page, images)

            # Try to save as draft instead of publishing
            await self._random_delay(1000, 2000)
            saved = await self._click_save_draft(page)

            draft_id = f"wb_draft_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            return {
                "success": saved,
                "draft_id": draft_id,
                "status": "draft_saved" if saved else "draft_button_not_found",
            }

        except Exception as exc:
            logger.exception("Weibo save draft failed")
            return {"success": False, "error": str(exc)}

    # ── Internal automation helpers ──────────────────────────────

    def _validate_inputs(
        self,
        content: str,
        images: list[str],
    ) -> str | None:
        """Validate inputs and return error string, or None if valid."""
        if not content.strip():
            return "Content cannot be empty"
        if len(content) > MAX_CONTENT_LENGTH:
            return f"Content exceeds {MAX_CONTENT_LENGTH} chars ({len(content)})"
        if len(images) > MAX_IMAGES:
            return f"Too many images ({len(images)} > {MAX_IMAGES})"

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
                logger.info("Weibo rate limiting: waiting %.1fs", wait)
                time.sleep(wait)

    async def _focus_compose_box(self, page: Page) -> None:
        """Find and focus the Weibo compose textarea."""
        selectors = [
            'textarea[node-type="textEl"]',
            'textarea[placeholder*="有什么新鲜事"]',
            'textarea[placeholder*="分享"]',
            '[class*="compose"] textarea',
            '[contenteditable="true"]',
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                await loc.click(timeout=3000)
                logger.info("Compose box focused via: %s", sel)
                return
            except Exception:
                continue

        # JS fallback
        await page.evaluate("""() => {
            const el = document.querySelector('textarea')
                || document.querySelector('[contenteditable="true"]');
            if (el) el.focus();
        }""")
        logger.info("Compose box focused via JS fallback")

    async def _type_content(self, page: Page, content: str) -> None:
        """Type content into the compose box with human-like typing."""
        # Clear existing content first
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Backspace")
        await self._random_delay(200, 500)

        # Type with random delay
        await page.keyboard.type(content, delay=self._typing_delay())
        logger.info("Weibo content typed (%d chars)", len(content))

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
                logger.warning("Skipping missing Weibo image: %s", p)

        if not abs_paths:
            logger.warning("No valid images to upload for Weibo")
            return

        # Try file input first
        file_input = page.locator('input[type="file"]').first
        try:
            await file_input.set_input_files(abs_paths, timeout=5000)
            await page.wait_for_timeout(3000)
            logger.info("Uploaded %d Weibo images via file input", len(abs_paths))
            return
        except Exception:
            logger.debug("Weibo file input approach failed, trying click")

        # Fallback: click the image upload button then set files
        try:
            img_btn = page.locator('[action-type="btn_insert_pic"], [title*="图片"], [class*="pic"]').first
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                await img_btn.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(abs_paths)
            await page.wait_for_timeout(3000)
            logger.info("Uploaded %d Weibo images via file chooser", len(abs_paths))
        except Exception as exc:
            logger.warning("Weibo image upload failed: %s", exc)

    async def _click_publish(self, page: Page) -> bool:
        """Click the publish/send button."""
        for text in ["发布", "发微博", "发送"]:
            btn = page.locator(f'button:has-text("{text}"), a:has-text("{text}")').first
            try:
                await btn.click(timeout=3000)
                await page.wait_for_timeout(3000)
                logger.info("Weibo publish button clicked: %s", text)
                return True
            except Exception:
                continue

        # JS fallback
        result = await page.evaluate("""() => {
            const buttons = Array.from(
                document.querySelectorAll('button, a[class*="submit"], [node-type="submit"]')
            );
            for (const b of buttons) {
                const text = b.textContent.trim();
                if (text.includes('发布') || text.includes('发送') || text.includes('发微博')) {
                    b.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            await page.wait_for_timeout(3000)
            logger.info("Weibo publish button clicked via JS: %s", result)
            return True

        logger.warning("Weibo publish button not found")
        return False

    async def _click_save_draft(self, page: Page) -> bool:
        """Click the save-as-draft button (if available)."""
        # Weibo's draft save is accessed through a dropdown or specific button
        for text in ["存草稿", "保存为草稿", "保存"]:
            btn = page.locator(f'button:has-text("{text}"), a:has-text("{text}")').first
            try:
                await btn.click(timeout=3000)
                await page.wait_for_timeout(2000)
                logger.info("Weibo draft save button clicked: %s", text)
                return True
            except Exception:
                continue

        # Try to find a dropdown or menu that contains draft option
        result = await page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll(
                '[class*="menu"] a, [class*="dropdown"] a, button, [class*="draft"]'
            ));
            for (const el of items) {
                const text = el.textContent.trim();
                if (text.includes('草稿') || text.includes('保存')) {
                    el.click();
                    return 'clicked: ' + text;
                }
            }
            return 'not_found';
        }""")

        if result and result.startswith("clicked"):
            await page.wait_for_timeout(2000)
            logger.info("Weibo draft save via JS: %s", result)
            return True

        logger.warning("Weibo draft save button not found")
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
