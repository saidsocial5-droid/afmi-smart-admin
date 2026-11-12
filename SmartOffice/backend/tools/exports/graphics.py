"""Graphiques des exports : SVG pour le HTML/PDF (comme l'éditeur), PNG haute définition pour Word.

Aucune bibliothèque de graphiques (pas de matplotlib) : barres horizontales « prévu / réalisé » et camemberts,
dessinés comme dans l'éditeur (BarChart.jsx, PieChart.jsx), aux couleurs de la charte.
"""
import io
import math
from html import escape
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont, features

PALETTE = ["#1B4332", "#D4A373", "#2D6A4F", "#BC6C25", "#52B788", "#7F5539", "#95D5B2", "#DDA15E", "#40916C", "#B08968"]
FONT_CANDIDATES = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf", "segoeui.ttf", "tahoma.ttf",
                   "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/tahoma.ttf"]


def palette(colors: Optional[Dict[str, str]]) -> List[str]:
    if colors and colors.get("primary"):
        return [colors["primary"], colors.get("secondary") or "#D4A373", *PALETTE[2:]]
    return PALETTE


def _fmt0(v: float) -> str:
    return f"{v:,.0f}".replace(",", "\u202f")


def _fmt2(v: float) -> str:
    return f"{v:,.2f}".replace(",", "\u202f").replace(".", ",")


def _short(label: str, n: int = 32) -> str:
    return label if len(label) <= n else label[: n - 1] + "…"


# --- SVG -----------------------------------------------------------------------------------------------------

def bars_svg(series: List[Dict[str, Any]], colors: Optional[Dict[str, str]], unit: str = "", legend: Optional[List[str]] = None) -> str:
    if not series:
        return '<div class="block-empty">Aucune donnée à représenter.</div>'
    legend = legend or ["Prévu", "Réalisé"]
    mx = max([max(s.get("planned") or 0, s.get("actual") or 0) for s in series] + [1])
    row_h, label_w, width = 34, 210, 640
    bar_w = width - label_w - 90
    height = len(series) * row_h + 30
    pal = palette(colors)
    parts = [f'<svg viewBox="0 0 {width} {height}" class="bar-chart" role="img" xmlns="http://www.w3.org/2000/svg">']
    for i, s in enumerate(series):
        y = 10 + i * row_h
        pw, aw = (s.get("planned") or 0) / mx * bar_w, (s.get("actual") or 0) / mx * bar_w
        parts.append(f'<text x="{label_w - 8}" y="{y + 16}" text-anchor="end" font-size="11" fill="#374151">{escape(_short(s["label"]))}</text>'
                     f'<rect x="{label_w}" y="{y + 2}" width="{pw:.1f}" height="11" fill="{pal[1]}" opacity="0.55"/>'
                     f'<rect x="{label_w}" y="{y + 15}" width="{aw:.1f}" height="11" fill="{pal[0]}"/>'
                     f'<text x="{label_w + max(pw, aw) + 6:.1f}" y="{y + 18}" font-size="10" fill="#374151">'
                     f'{_fmt0(s.get("actual") or 0)} / {_fmt0(s.get("planned") or 0)} {escape(unit)}</text>')
    parts.append(f'<g transform="translate({label_w}, {height - 12})" font-size="10" fill="#374151">'
                 f'<rect width="10" height="8" fill="{pal[1]}" opacity="0.55"/><text x="14" y="8">{escape(legend[0])}</text>'
                 f'<rect x="70" width="10" height="8" fill="{pal[0]}"/><text x="84" y="8">{escape(legend[1])}</text></g></svg>')
    return "".join(parts)


def pie_svg(slices: List[Dict[str, Any]], colors: Optional[Dict[str, str]]) -> str:
    total = sum(s["value"] for s in slices)
    if not total:
        return ""
    pal = palette(colors)
    r, cx, cy = 70, 80, 80
    angle = -math.pi / 2
    paths = []
    for i, s in enumerate(slices):
        a = s["value"] / total * 2 * math.pi
        x1, y1 = cx + r * math.cos(angle), cy + r * math.sin(angle)
        angle += a
        x2, y2 = cx + r * math.cos(angle), cy + r * math.sin(angle)
        d = (f"M {cx - r} {cy} a {r} {r} 0 1 0 {2 * r} 0 a {r} {r} 0 1 0 {-2 * r} 0" if len(slices) == 1
             else f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {r} {r} 0 {1 if a > math.pi else 0} 1 {x2:.2f} {y2:.2f} Z")
        paths.append(f'<path d="{d}" fill="{pal[i % len(pal)]}" stroke="#fff" stroke-width="1"/>')
    return f'<svg viewBox="0 0 160 160" class="pie-svg" xmlns="http://www.w3.org/2000/svg">{"".join(paths)}</svg>'


# --- PNG (Word) ---------------------------------------------------------------------------------------------

def _font(size: int):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size, layout_engine=ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", dpi=(200, 200), optimize=True)
    return buf.getvalue()


def bars_png(series: List[Dict[str, Any]], colors: Optional[Dict[str, str]], unit: str = "", legend: Optional[List[str]] = None,
             rtl: bool = False) -> Optional[bytes]:
    """Même dessin que bars_svg, à l'échelle 3 (impression nette)."""
    if not series:
        return None
    k = 3
    legend = legend or ["Prévu", "Réalisé"]
    mx = max([max(s.get("planned") or 0, s.get("actual") or 0) for s in series] + [1])
    row_h, label_w, width = 34 * k, 210 * k, 640 * k
    bar_w = width - label_w - 90 * k
    height = len(series) * row_h + 30 * k
    pal = palette(colors)
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    f11, f10 = _font(11 * k), _font(10 * k)
    secondary = tuple(int(255 - (255 - c) * 0.55) for c in _rgb(pal[1]))   # opacité 0,55 sur fond blanc
    for i, s in enumerate(series):
        y = 10 * k + i * row_h
        pw, aw = (s.get("planned") or 0) / mx * bar_w, (s.get("actual") or 0) / mx * bar_w
        label = _short(s["label"])
        d.text((label_w - 8 * k, y + 16 * k), label, font=f11, fill="#374151", anchor="rs",
               direction="rtl" if rtl and features.check("raqm") else None)
        d.rectangle([label_w, y + 2 * k, label_w + pw, y + 13 * k], fill=secondary)
        d.rectangle([label_w, y + 15 * k, label_w + aw, y + 26 * k], fill=pal[0])
        d.text((label_w + max(pw, aw) + 6 * k, y + 18 * k), f"{_fmt0(s.get('actual') or 0)} / {_fmt0(s.get('planned') or 0)} {unit}",
               font=f10, fill="#374151", anchor="ls")
    ly = height - 12 * k
    d.rectangle([label_w, ly, label_w + 10 * k, ly + 8 * k], fill=secondary)
    d.text((label_w + 14 * k, ly + 8 * k), legend[0], font=f10, fill="#374151", anchor="ls")
    d.rectangle([label_w + 70 * k, ly, label_w + 80 * k, ly + 8 * k], fill=pal[0])
    d.text((label_w + 84 * k, ly + 8 * k), legend[1], font=f10, fill="#374151", anchor="ls")
    return _png(img)


def pie_png(slices: List[Dict[str, Any]], colors: Optional[Dict[str, str]]) -> Optional[bytes]:
    """Camembert seul (la légende chiffrée est un tableau Word, sélectionnable et traduisible)."""
    total = sum(s["value"] for s in slices)
    if not total:
        return None
    k = 4
    size = 160 * k
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    pal = palette(colors)
    start = -90.0
    box = [10 * k, 10 * k, 150 * k, 150 * k]
    for i, s in enumerate(slices):
        extent = s["value"] / total * 360
        d.pieslice(box, start, start + extent, fill=pal[i % len(pal)], outline="white", width=k)
        start += extent
    return _png(img)


def pie_legend(slices: List[Dict[str, Any]]) -> List[List[str]]:
    total = sum(s["value"] for s in slices) or 1
    return [[s["label"], f"{_fmt2(s['value'])} MAD", f"{100 * s['value'] / total:.1f}".replace(".", ",") + " %"] for s in slices]
