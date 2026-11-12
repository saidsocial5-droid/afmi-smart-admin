"""Convertit GUIDE_UTILISATEUR.md en page HTML autonome (images intégrées) pour l'installateur.

Usage : python docs/v2/captures/guide_html.py <sortie.html>
Ne gère que la syntaxe utilisée par le guide : titres, paragraphes, listes, tableaux, citations, images, gras, code.
"""
import base64
import html
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "GUIDE_UTILISATEUR.md"


def inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", t)


def convert(md: str, base: Path) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.strip() == "---":
            out.append("<hr/>")
        elif m := re.match(r"!\[(.*?)\]\((.+?)\)", line.strip()):
            img = (base / m.group(2)).read_bytes()
            out.append(f'<figure><img alt="{html.escape(m.group(1))}" src="data:image/png;base64,{base64.b64encode(img).decode()}"/>'
                       f"<figcaption>{inline(m.group(1))}</figcaption></figure>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s:|-]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:]) + "</tbody></table>")
            continue
        elif re.match(r"^(\s*)([-*]|\d+\.) ", line):
            ordered = bool(re.match(r"^\s*\d+\.", line))
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.) ", lines[i]) or (lines[i].startswith("  ") and lines[i].strip())):
                if re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> "))
                i += 1
            out.append(f"<blockquote>{inline(' '.join(quote))}</blockquote>")
            continue
        else:
            para = [line]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||!\[|>|---|\s*([-*]|\d+\.) )", lines[i + 1]):
                i += 1
                para.append(lines[i])
            out.append(f"<p>{inline(' '.join(p.strip() for p in para))}</p>")
        i += 1
    return "\n".join(out)


def main(target: str) -> None:
    body = convert(SRC.read_text(encoding="utf-8"), SRC.parent)
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Guide utilisateur — AFMI Smart Admin 2.0</title><style>
body {{ font-family: "Segoe UI", Calibri, Arial, sans-serif; max-width: 980px; margin: 0 auto; padding: 24px 16px; color: #1F2937; line-height: 1.55; background: #fff; }}
h1, h2, h3 {{ color: #1B4332; }} h2 {{ border-bottom: 2px solid #D4A373; padding-bottom: 4px; margin-top: 2em; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }} th, td {{ border: 1px solid #CBD5E1; padding: 6px 8px; text-align: start; vertical-align: top; }}
th {{ background: #1B4332; color: #fff; }} figure {{ margin: 16px 0; }} img {{ max-width: 100%; border: 1px solid #E2E8F0; border-radius: 6px; }}
figcaption {{ font-size: 13px; color: #6B7280; }} blockquote {{ border-inline-start: 4px solid #D4A373; margin: 12px 0; padding: 4px 12px; background: #FFFBEB; }}
code {{ background: #F1F5F9; padding: 1px 4px; border-radius: 3px; }}
</style></head><body>{body}</body></html>"""
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "GUIDE_UTILISATEUR.html")
