"""Static accessibility checks for the preview pages."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    ROOT / "src/voya/web/index.html",
    ROOT / "src/voya/web/invite.html",
    ROOT / "src/voya/web/privacy.html",
    ROOT / "src/voya/web/terms.html",
]


def _channel(value: int) -> float:
    channel = value / 255
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _luminance(color: str) -> float:
    red, green, blue = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter = max(_luminance(foreground), _luminance(background))
    darker = min(_luminance(foreground), _luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


class _Controls(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.skip = False
        self._label_depth = 0
        self.unlabeled: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self.lang = data.get("lang") or ""
        if tag == "a" and data.get("href") == "#main":
            self.skip = True
        if tag == "label":
            self._label_depth += 1
        if tag in {"input", "select", "textarea"}:
            labeled = self._label_depth > 0 or bool(
                data.get("aria-label") or data.get("aria-labelledby")
            )
            if data.get("type") == "hidden":
                return
            if not labeled:
                self.unlabeled.append(tag)
        if tag == "button":
            self._buttons = getattr(self, "_buttons", [])
            self._buttons.append(data.get("aria-label") or "")
            self._open_button = True
        if tag == "img" and not data.get("alt"):
            self.unlabeled.append("img")

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self._label_depth:
            self._label_depth -= 1
        if tag == "button":
            self._open_button = False

    def handle_data(self, data: str) -> None:
        if getattr(self, "_open_button", False) and data.strip():
            self._buttons[-1] = data.strip()


def test_pages_have_language_and_labeled_controls() -> None:
    for path in PAGES:
        parser = _Controls()
        parser.feed(path.read_text(encoding="utf-8"))
        assert parser.lang == "en", path.name
        assert parser.unlabeled == [], path.name
    home = (ROOT / "src/voya/web/index.html").read_text(encoding="utf-8")
    assert 'href="#main"' in home
    assert 'id="main"' in home
    buttons = _Controls()
    buttons.feed(home)
    assert all(name.strip() for name in buttons._buttons)


def test_text_colors_clear_wcag_aa() -> None:
    pairs = [
        ("#5d6762", "#ffffff"),
        ("#1d2320", "#f6f5f1"),
        ("#1f6f5c", "#ffffff"),
        ("#ffffff", "#6d3b00"),
        ("#ffffff", "#1f6f5c"),
        ("#5a4300", "#fff3d6"),
        ("#a3ada8", "#111513"),
    ]
    for foreground, background in pairs:
        assert _contrast(foreground, background) >= 4.5


def test_stylesheet_declares_a_visible_focus() -> None:
    css = (ROOT / "src/voya/web/styles.css").read_text(encoding="utf-8")
    assert re.search(r":focus-visible\s*\{[^}]*outline", css)
