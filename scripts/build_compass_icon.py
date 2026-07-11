#!/usr/bin/env python3
"""Build a Windows .ico with a compass emoji for the Net Command Comparator shortcut."""

from __future__ import annotations

import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "compass_logo.ico"
EMOJI = "\U0001f9ed"  # 🧭
SIZES = (256, 128, 64, 48, 32, 16)

WIN_EMOJI_FONT = Path(r"C:\Windows\Fonts\seguiemj.ttf")
FALLBACK_FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")


def _font_for_size(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (WIN_EMOJI_FONT, FALLBACK_FONT):
        if path.exists():
            return ImageFont.truetype(str(path), int(size * 0.82))
    return ImageFont.load_default()


def _render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font_for_size(size)
    bbox = draw.textbbox((0, 0), EMOJI, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), EMOJI, font=font, embedded_color=True)
    return img


def main() -> int:
    if platform.system() != "Windows":
        print("Compass emoji icon is tuned for Windows (Segoe UI Emoji).")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    icons = [_render(size) for size in SIZES]
    icons[0].save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=icons[1:],
    )
    print(f"Icon written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())