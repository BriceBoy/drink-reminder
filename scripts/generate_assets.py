"""Generate original artwork; no external image downloads."""

from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent.parent / "water_reminder" / "assets"


def droplet(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str) -> None:
    draw.polygon(
        [
            (x + size // 2, y),
            (x + size // 10, y + size * 3 // 5),
            (x + size * 9 // 10, y + size * 3 // 5),
        ],
        fill=color,
    )
    draw.ellipse((x, y + size // 3, x + size, y + size * 4 // 3), fill=color)
    draw.ellipse((x + size // 5, y + size // 2, x + size // 3, y + size * 4 // 5), fill="#b9ecff")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = Image.new("RGBA", (256, 256))
    draw = ImageDraw.Draw(icon)
    draw.rounded_rectangle((4, 4, 252, 252), radius=56, fill="#e8f5fc")
    droplet(draw, 62, 20, 132, "#168ed1")
    icon.save(ASSETS / "water.png")
    icon.save(ASSETS / "water.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)])


if __name__ == "__main__":
    main()
