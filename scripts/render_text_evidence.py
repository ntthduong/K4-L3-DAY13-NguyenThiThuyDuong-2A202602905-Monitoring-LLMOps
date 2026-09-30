from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render(source: Path, output: Path) -> None:
    text = source.read_text(encoding="utf-8")
    lines: list[str] = []
    for original in text.splitlines():
        lines.extend(textwrap.wrap(original, width=105, replace_whitespace=False) or [""])

    font_path = Path(r"C:\Windows\Fonts\consola.ttf")
    font = ImageFont.truetype(str(font_path), 22) if font_path.exists() else ImageFont.load_default()
    line_height = 30
    width = 1600
    height = max(300, 80 + line_height * len(lines))
    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 54), fill="#161b22")
    draw.text((24, 15), f"Evidence export: {source.name}", font=font, fill="#58a6ff")
    y = 70
    for line in lines:
        draw.text((24, y), line, font=font, fill="#e6edf3")
        y += line_height
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an exact UTF-8 evidence export as a readable PNG")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.source, args.output)
    print(f"Rendered {args.source} -> {args.output}")


if __name__ == "__main__":
    main()
