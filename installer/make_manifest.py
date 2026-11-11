"""Manifeste de mise à jour (latest.json) d'une version publiée d'AFMI Smart Admin.

Usage : python installer/make_manifest.py <installateur.exe> <version> <dépôt_de_publication> <sortie.json>
Le manifeste est ensuite signé par le workflow (openssl dgst -sha256 -sign, clé secrète UPDATE_SIGNING_KEY) ;
l'application refuse tout manifeste dont la signature n'est pas valide (Core/Services/UpdateVerifier.cs).
"""
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release_notes(version: str, changelog: Path = ROOT / "CHANGELOG.md", limit: int = 600) -> str:
    """Titre et premières lignes « Ajouté » de la version dans le CHANGELOG, en texte simple et court (bandeau)."""
    text = changelog.read_text(encoding="utf-8") if changelog.exists() else ""
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
    if not m:
        return f"Version {version}."
    head = re.search(rf"^## \[{re.escape(version)}\] — [^—]*— (.*)$", text, re.M)
    bullets = [re.sub(r"\*\*|`", "", b).strip() for b in re.findall(r"^- (.+)$", m.group(1), re.M)]
    out = (head.group(1).strip() + ". " if head else "") + " · ".join(b.split(" :")[0].rstrip(".") for b in bullets[:6])
    return out if len(out) <= limit else out[: limit - 1].rstrip() + "…"


def build(installer: Path, version: str, repo: str) -> dict:
    data = installer.read_bytes()
    return {
        "product": "AFMI Smart Admin",
        "version": version,
        "published": date.today().isoformat(),
        "url": f"https://github.com/{repo}/releases/download/v{version}/{installer.name}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "notes": release_notes(version),
    }


if __name__ == "__main__":
    exe, ver, repo, out = sys.argv[1:5]
    manifest = build(Path(exe), ver, repo)
    # Octets exacts signés puis vérifiés : UTF-8 sans BOM, sans fin de ligne ajoutée
    Path(out).write_bytes(json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"))
    print(json.dumps(manifest, ensure_ascii=False, indent=1))
