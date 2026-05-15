"""Template-based image card generator for XHS carousel slides."""

from __future__ import annotations

import io
import logging
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[3]  # backend/
ASSETS_DIR = _ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
TEMPLATES_DIR = ASSETS_DIR / "templates"


@dataclass
class CardStyle:
    """Visual style configuration for cards."""

    background_color: str = "#1a1a2e"
    accent_color: str = "#c2714f"
    text_color: str = "#ffffff"
    font_name: str = "NotoSansSC"
    title_size: int = 72
    body_size: int = 36
    card_width: int = 1080
    card_height: int = 1440
    padding: int = 80


# ── Built-in preset styles ──

PRESET_STYLES: dict[str, CardStyle] = {
    "dark_elegant": CardStyle(
        background_color="#1a1a2e",
        accent_color="#c2714f",
        text_color="#ffffff",
    ),
    "warm_cream": CardStyle(
        background_color="#faf3e8",
        accent_color="#c87b5a",
        text_color="#2d2016",
    ),
    "ocean_blue": CardStyle(
        background_color="#0f1b2d",
        accent_color="#4fc3f7",
        text_color="#e0f0ff",
    ),
    "forest_green": CardStyle(
        background_color="#1a2e1a",
        accent_color="#81c784",
        text_color="#e8f5e9",
    ),
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#rrggbb' to (r, g, b)."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class VisualEngine:
    """Generate XHS carousel cards with text overlay."""

    def __init__(self) -> None:
        self._font_cache: dict[str, ImageFont.FreeTypeFont] = {}

    # ── Public API ──

    async def generate_carousel(
        self,
        title: str,
        slides: list[dict],
        style: CardStyle | None = None,
    ) -> list[bytes]:
        """Generate a complete carousel (cover + content slides + CTA).

        Args:
            title: Main title for the cover slide.
            slides: List of dicts with keys ``text`` and optional ``subtitle``.
            style: Visual style; defaults to ``dark_elegant``.

        Returns:
            List of PNG bytes — one per slide.
        """
        style = style or PRESET_STYLES["dark_elegant"]
        result: list[bytes] = []

        # Cover
        subtitle = slides[0].get("subtitle", "") if slides else ""
        result.append(await self.generate_cover(title, subtitle, style))

        # Content slides
        for idx, slide in enumerate(slides):
            result.append(
                await self.generate_content_slide(
                    text=slide["text"],
                    slide_number=idx + 1,
                    total_slides=len(slides),
                    style=style,
                )
            )

        # CTA
        cta_text = slides[-1].get("subtitle", "关注我，获取更多精彩内容") if slides else "关注我"
        result.append(await self.generate_cta_slide(cta_text, style))

        return result

    async def generate_cover(
        self, title: str, subtitle: str, style: CardStyle
    ) -> bytes:
        """Generate cover slide with large title."""
        img = self._create_base_card(style)
        draw = ImageDraw.Draw(img)

        # Decorative accent bar
        bar_y = style.padding
        draw.rectangle(
            [style.padding, bar_y, style.padding + 120, bar_y + 6],
            fill=_hex_to_rgb(style.accent_color),
        )

        # Title — centred vertically
        title_font = self._load_font(style.font_name, style.title_size, bold=True)
        self._draw_text_block(
            draw,
            title,
            position=(style.padding, style.card_height // 3),
            max_width=style.card_width - style.padding * 2,
            font=title_font,
            fill=_hex_to_rgb(style.text_color),
            line_spacing=int(style.title_size * 0.4),
        )

        # Subtitle
        if subtitle:
            sub_font = self._load_font(style.font_name, style.body_size)
            self._draw_text_block(
                draw,
                subtitle,
                position=(style.padding, style.card_height * 2 // 3),
                max_width=style.card_width - style.padding * 2,
                font=sub_font,
                fill=_hex_to_rgb(style.accent_color),
                line_spacing=int(style.body_size * 0.3),
            )

        return self._to_png(img)

    async def generate_content_slide(
        self,
        text: str,
        slide_number: int,
        total_slides: int = 1,
        style: CardStyle | None = None,
    ) -> bytes:
        """Generate a single content slide."""
        style = style or PRESET_STYLES["dark_elegant"]
        img = self._create_base_card(style)
        draw = ImageDraw.Draw(img)

        # Slide number badge
        badge_font = self._load_font(style.font_name, 28)
        badge_text = f"{slide_number}/{total_slides}"
        draw.rounded_rectangle(
            [style.padding, style.padding, style.padding + 100, style.padding + 48],
            radius=8,
            fill=_hex_to_rgb(style.accent_color),
        )
        draw.text(
            (style.padding + 16, style.padding + 8),
            badge_text,
            font=badge_font,
            fill=_hex_to_rgb(style.text_color),
        )

        # Content text — starts below badge
        content_y = style.padding + 80
        body_font = self._load_font(style.font_name, style.body_size)
        self._draw_text_block(
            draw,
            text,
            position=(style.padding, content_y),
            max_width=style.card_width - style.padding * 2,
            font=body_font,
            fill=_hex_to_rgb(style.text_color),
            line_spacing=int(style.body_size * 0.6),
        )

        # Bottom accent line
        line_y = style.card_height - style.padding
        draw.rectangle(
            [style.padding, line_y, style.card_width - style.padding, line_y + 4],
            fill=_hex_to_rgb(style.accent_color),
        )

        return self._to_png(img)

    async def generate_cta_slide(self, cta_text: str, style: CardStyle) -> bytes:
        """Generate closing CTA slide."""
        img = self._create_base_card(style)
        draw = ImageDraw.Draw(img)

        # CTA text — centred
        cta_font = self._load_font(style.font_name, style.title_size, bold=True)
        self._draw_text_block(
            draw,
            cta_text,
            position=(style.padding, style.card_height // 3),
            max_width=style.card_width - style.padding * 2,
            font=cta_font,
            fill=_hex_to_rgb(style.accent_color),
            line_spacing=int(style.title_size * 0.4),
            align="center",
        )

        # Decorative bottom bar
        bar_w = 200
        bar_x = (style.card_width - bar_w) // 2
        bar_y = style.card_height * 2 // 3
        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + 6],
            fill=_hex_to_rgb(style.text_color),
        )

        # Small prompt
        small_font = self._load_font(style.font_name, 28)
        prompt = "点赞 + 收藏 + 关注"
        bbox = small_font.getbbox(prompt)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((style.card_width - tw) // 2, bar_y + 30),
            prompt,
            font=small_font,
            fill=_hex_to_rgb(style.text_color),
        )

        return self._to_png(img)

    # ── Internals ──

    def _create_base_card(self, style: CardStyle) -> Image.Image:
        """Create blank card with background colour."""
        return Image.new(
            "RGB",
            (style.card_width, style.card_height),
            color=_hex_to_rgb(style.background_color),
        )

    def _draw_text_block(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        *,
        position: tuple[int, int],
        max_width: int,
        font: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int],
        line_spacing: int = 10,
        align: str = "left",
    ) -> None:
        """Draw text with auto-wrapping and styling.

        Uses ``textwrap`` for CJK-aware wrapping (approximation) and draws each
        line manually to support custom line spacing.
        """
        # Estimate chars per line from average glyph width
        sample = "测试文字ABCD"
        bbox = font.getbbox(sample)
        avg_char_width = max((bbox[2] - bbox[0]) / len(sample), 1)
        chars_per_line = max(int(max_width / avg_char_width), 1)

        wrapped = textwrap.fill(text, width=chars_per_line)
        lines = wrapped.split("\n")

        x, y = position
        for line in lines:
            if align == "center":
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0]
                lx = x + (max_width - line_w) // 2
            else:
                lx = x
            draw.text((lx, y), line, font=font, fill=fill)
            line_h = font.getbbox(line)[3] - font.getbbox(line)[1]
            y += line_h + line_spacing

    def _load_font(
        self, name: str, size: int, bold: bool = False
    ) -> ImageFont.FreeTypeFont:
        """Load font from assets directory with system-font fallback."""
        cache_key = f"{name}:{size}:{bold}"
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = self._try_load_font(name, size, bold)
        self._font_cache[cache_key] = font
        return font

    def _try_load_font(
        self, name: str, size: int, bold: bool
    ) -> ImageFont.FreeTypeFont:
        """Try multiple font paths, falling back to default."""
        suffix = "-Bold" if bold else "-Regular"
        candidates = [
            FONTS_DIR / f"{name}{suffix}.ttf",
            FONTS_DIR / f"{name}{suffix}.otf",
            FONTS_DIR / f"{name}.ttf",
            FONTS_DIR / f"{name}.otf",
        ]

        # Also try well-known system CJK fonts
        system_fonts = [
            Path("C:/Windows/Fonts/msyh.ttc"),      # Microsoft YaHei
            Path("C:/Windows/Fonts/msyhbd.ttc"),     # Microsoft YaHei Bold
            Path("C:/Windows/Fonts/simsun.ttc"),     # SimSun
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansSC-Regular.ttf"),
        ]

        for path in candidates:
            if path.exists():
                try:
                    font = ImageFont.truetype(str(path), size)
                    logger.info("Loaded font: %s", path)
                    return font
                except OSError:
                    continue

        # System font fallback
        for path in system_fonts:
            if path.exists():
                try:
                    font = ImageFont.truetype(str(path), size)
                    logger.info("Loaded system font: %s", path)
                    return font
                except OSError:
                    continue

        logger.warning(
            "No CJK font found for %s; falling back to Pillow default", name
        )
        return ImageFont.load_default()

    @staticmethod
    def _to_png(img: Image.Image) -> bytes:
        """Serialise a PIL Image to PNG bytes."""
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
