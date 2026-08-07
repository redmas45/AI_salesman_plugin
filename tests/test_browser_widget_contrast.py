"""The widget's own text stays readable on any host's brand colour.

Reported (local, 2026-08-07): "Listening..." rendered as near-white text on the
widget's near-white panel and was effectively invisible. The widget borrows its
accent from the host page's `<meta name="theme-color">`, and AI-KART publishes
`#fbf7f3`. Any pale-themed host reproduces it, so the fix is a contrast rule
rather than a colour choice.

WCAG 2.1 requires 4.5:1 for body text; these cases pin that the derived accent
meets it whatever the host publishes.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
STYLES = ROOT / "plugin" / "src" / "widget" / "styles.js"

# Relative luminance and contrast, per WCAG 2.1, recomputed here so the test does
# not trust the implementation's own arithmetic.
def _luminance(rgb):
    channels = []
    for value in rgb:
        scaled = value / 255
        channels.append(scaled / 12.92 if scaled <= 0.03928 else ((scaled + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first, second):
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _parse(value):
    text = value.strip()
    if text.startswith("#"):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(character * 2 for character in digits)
        return [int(digits[index : index + 2], 16) for index in (0, 2, 4)]
    inner = text[text.index("(") + 1 : text.index(")")]
    return [int(float(part)) for part in inner.split(",")[:3]]


def _readable_accent(primary, text_color, is_dark):
    """Run the shipped implementation through node."""
    script = f"""
    import {{ readableAccent }} from "file://{STYLES.as_posix()}";
    process.stdout.write(readableAccent({primary!r}, {text_color!r}, {str(is_dark).lower()}));
    """
    result = subprocess.run(
        [_node(), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        pytest.fail(f"node failed: {result.stderr[:400]}")
    return result.stdout.strip()


def _node():
    import shutil

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available to evaluate the widget stylesheet")
    return node


LIGHT_SURFACE = [255, 255, 255]
DARK_SURFACE = [24, 24, 27]
LIGHT_TEXT = "#111827"


@pytest.mark.parametrize(
    "theme_color",
    [
        "#fbf7f3",  # the reported AI-KART cream that caused the defect
        "#ffffff",
        "#fffef0",
        "rgb(250, 250, 250)",
        "#5d5fef",  # already-legible indigo, must pass through unchanged in spirit
        "#000000",
    ],
)
def test_the_derived_accent_is_readable_on_the_light_panel(theme_color):
    accent = _readable_accent(theme_color, LIGHT_TEXT, False)
    assert _contrast(_parse(accent), LIGHT_SURFACE) >= 4.5, f"{theme_color} -> {accent}"


@pytest.mark.parametrize("theme_color", ["#111827", "#000000", "#1a1a1a", "#fbf7f3"])
def test_the_derived_accent_is_readable_on_the_dark_panel(theme_color):
    accent = _readable_accent(theme_color, "#f3f4f6", True)
    assert _contrast(_parse(accent), DARK_SURFACE) >= 4.5, f"{theme_color} -> {accent}"


def test_a_legible_brand_colour_is_kept_exactly():
    """A host whose colour already works keeps its own branding."""
    assert _readable_accent("#5d5fef", LIGHT_TEXT, False) == "#5d5fef"


def test_an_unparseable_colour_falls_back_to_body_text():
    assert _readable_accent("not-a-colour", LIGHT_TEXT, False) == LIGHT_TEXT
