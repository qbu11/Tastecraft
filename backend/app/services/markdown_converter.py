"""Convert Markdown to WeChat-compatible HTML with inline styles.

WeChat Official Account articles strip all <style> tags and most CSS classes,
so every element must carry its own inline ``style`` attribute.
"""

from __future__ import annotations

import html
import re


# ── Inline style tokens ──────────────────────────────────────────────────────

_STYLES = {
    "body": (
        "font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', "
        "'PingFang SC', 'Microsoft YaHei', sans-serif; "
        "font-size: 16px; line-height: 1.8; color: #333; "
        "padding: 0; margin: 0;"
    ),
    "h1": (
        "font-size: 22px; font-weight: bold; color: #1a1a1a; "
        "margin: 28px 0 16px 0; line-height: 1.4;"
    ),
    "h2": (
        "font-size: 20px; font-weight: bold; color: #1a1a1a; "
        "margin: 24px 0 12px 0; line-height: 1.4;"
    ),
    "h3": (
        "font-size: 18px; font-weight: bold; color: #1a1a1a; "
        "margin: 20px 0 10px 0; line-height: 1.4;"
    ),
    "p": "margin: 12px 0; line-height: 1.8;",
    "blockquote": (
        "border-left: 3px solid #ddd; padding: 8px 16px; "
        "margin: 16px 0; color: #666; background: #f9f9f9;"
    ),
    "code_inline": (
        "background: #f5f5f5; padding: 2px 6px; border-radius: 3px; "
        "font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; "
        "font-size: 14px; color: #e83e8c;"
    ),
    "code_block": (
        "background: #2d2d2d; color: #ccc; padding: 16px; "
        "border-radius: 6px; overflow-x: auto; font-size: 14px; "
        "font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; "
        "line-height: 1.6; margin: 16px 0; white-space: pre-wrap; word-break: break-all;"
    ),
    "ul": "margin: 12px 0; padding-left: 24px; list-style-type: disc;",
    "ol": "margin: 12px 0; padding-left: 24px; list-style-type: decimal;",
    "li": "margin: 4px 0; line-height: 1.8;",
    "a": "color: #576b95; text-decoration: none;",
    "img": "max-width: 100%; height: auto; margin: 12px 0; border-radius: 4px;",
    "hr": "border: none; border-top: 1px solid #eee; margin: 24px 0;",
    "strong": "font-weight: bold; color: #1a1a1a;",
    "em": "font-style: italic;",
}


def _s(tag: str) -> str:
    """Return the inline style string for *tag*."""
    return _STYLES.get(tag, "")


# ── Converter ─────────────────────────────────────────────────────────────────

_RE_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_RE_CODE_BLOCK = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_RE_BLOCKQUOTE = re.compile(r"^>\s?(.+)$", re.MULTILINE)
_RE_UL = re.compile(r"^[-*]\s+(.+)$", re.MULTILINE)
_RE_OL = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
_RE_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_RE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_RE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_RE_CODE_INLINE = re.compile(r"`([^`]+)`")
_RE_HR = re.compile(r"^---+$", re.MULTILINE)


def markdown_to_wechat_html(md: str) -> str:
    """Convert a Markdown string to WeChat-compatible HTML with inline styles.

    The converter handles:
    - Headings (h1 -- h3)
    - Fenced code blocks (with dark background)
    - Inline code
    - Bold / italic
    - Unordered & ordered lists
    - Blockquotes
    - Images & links
    - Horizontal rules
    - Plain paragraphs
    """
    if not md or not md.strip():
        return ""

    result = md

    # 1. Fenced code blocks (must be first to avoid inner pattern matching)
    def _code_block_repl(m: re.Match) -> str:
        code = html.escape(m.group(2).strip())
        return f'<pre style="{_s("code_block")}"><code>{code}</code></pre>'

    result = _RE_CODE_BLOCK.sub(_code_block_repl, result)

    # 2. Headings
    def _heading_repl(m: re.Match) -> str:
        level = len(m.group(1))
        tag = f"h{level}"
        text = m.group(2).strip()
        return f'<{tag} style="{_s(tag)}">{text}</{tag}>'

    result = _RE_HEADING.sub(_heading_repl, result)

    # 3. Horizontal rules
    result = _RE_HR.sub(f'<hr style="{_s("hr")}"/>', result)

    # 4. Blockquotes
    def _blockquote_repl(m: re.Match) -> str:
        text = m.group(1).strip()
        return f'<div style="{_s("blockquote")}">{text}</div>'

    result = _RE_BLOCKQUOTE.sub(_blockquote_repl, result)

    # 5. Images (before links to avoid conflict)
    def _img_repl(m: re.Match) -> str:
        alt = html.escape(m.group(1))
        src = m.group(2)
        return f'<img src="{src}" alt="{alt}" style="{_s("img")}"/>'

    result = _RE_IMG.sub(_img_repl, result)

    # 6. Links
    def _link_repl(m: re.Match) -> str:
        text = m.group(1)
        href = m.group(2)
        return f'<a href="{href}" style="{_s("a")}">{text}</a>'

    result = _RE_LINK.sub(_link_repl, result)

    # 7. Inline styles
    result = _RE_BOLD.sub(rf'<strong style="{_s("strong")}">\1</strong>', result)
    result = _RE_ITALIC.sub(rf'<em style="{_s("em")}">\1</em>', result)
    result = _RE_CODE_INLINE.sub(rf'<code style="{_s("code_inline")}">\1</code>', result)

    # 8. Lists — simple per-line conversion
    #    Collect consecutive list items into <ul>/<ol> blocks.
    lines = result.split("\n")
    converted: list[str] = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()
        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)

        if ul_match:
            if not in_ul:
                if in_ol:
                    converted.append("</ol>")
                    in_ol = False
                converted.append(f'<ul style="{_s("ul")}">')
                in_ul = True
            converted.append(f'<li style="{_s("li")}">{ul_match.group(1)}</li>')
        elif ol_match:
            if not in_ol:
                if in_ul:
                    converted.append("</ul>")
                    in_ul = False
                converted.append(f'<ol style="{_s("ol")}">')
                in_ol = True
            converted.append(f'<li style="{_s("li")}">{ol_match.group(1)}</li>')
        else:
            if in_ul:
                converted.append("</ul>")
                in_ul = False
            if in_ol:
                converted.append("</ol>")
                in_ol = False
            converted.append(line)

    if in_ul:
        converted.append("</ul>")
    if in_ol:
        converted.append("</ol>")

    result = "\n".join(converted)

    # 9. Wrap remaining bare text lines in <p> tags
    final_lines: list[str] = []
    for line in result.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that already have block-level HTML
        if re.match(r"<(h[1-3]|p|div|ul|ol|li|pre|hr|img|table|blockquote)", stripped):
            final_lines.append(stripped)
        elif stripped.startswith("</"):
            final_lines.append(stripped)
        else:
            final_lines.append(f'<p style="{_s("p")}">{stripped}</p>')

    return "\n".join(final_lines)
