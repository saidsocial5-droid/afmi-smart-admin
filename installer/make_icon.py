"""Icônes de l'application à partir du logo de l'association (branding/logo.png, carré de préférence, 512 px ou plus).

Produit : branding/app.ico (application de bureau, installateur, backend ; 16 à 256 px) et
SmartOffice/frontend/public/favicon.png (onglet et fenêtre Smart Office). Sans logo, rien n'est fait.
Usage : python installer/make_icon.py
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "branding" / "logo.png"
ICON = ROOT / "branding" / "icon.png"      # facultatif : version compacte du logo pour les petites tailles


def square(img: Image.Image) -> Image.Image:
    """Logo centré sur un carré transparent (sans déformation)."""
    img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return canvas


def main() -> int:
    if not LOGO.exists():
        print("Pas de branding/logo.png : icônes par défaut.")
        return 0
    img = square(Image.open(ICON if ICON.exists() else LOGO))
    big = img.resize((256, 256), Image.LANCZOS)
    big.save(ROOT / "branding" / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    public = ROOT / "SmartOffice" / "frontend" / "public"
    public.mkdir(parents=True, exist_ok=True)
    img.resize((128, 128), Image.LANCZOS).save(public / "favicon.png")
    print("[OK] Icônes : branding/app.ico, SmartOffice/frontend/public/favicon.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
