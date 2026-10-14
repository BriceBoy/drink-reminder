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
    hero = Image.new("RGB", (720, 360), "#e8f5fc")
    draw = ImageDraw.Draw(hero)
    draw.ellipse((410, 40, 700, 330), fill="#d3ecf9")
    draw.rounded_rectangle((105, 64, 292, 303), radius=24, fill="white", outline="#168ed1", width=8)
    draw.rounded_rectangle((118, 160, 279, 289), radius=16, fill="#68c3ed")
    draw.ellipse((118, 150, 279, 183), fill="#9eddfa")
    droplet(draw, 457, 55, 139, "#168ed1")
    hero.save(ASSETS / "hydration.png")


if __name__ == "__main__":
    main()
