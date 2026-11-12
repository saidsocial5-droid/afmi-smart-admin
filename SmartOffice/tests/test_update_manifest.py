"""Manifeste de mise à jour : contenu, empreinte et notes tirées du CHANGELOG."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("make_manifest", ROOT / "installer" / "make_manifest.py")
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)


def test_manifest_fields(tmp_path):
    exe = tmp_path / "AFMI_Smart_Admin_Setup_9.9.9.exe"
    exe.write_bytes(b"installateur")
    m = mm.build(exe, "9.9.9", "saidsocial5-droid/afmi-smart-admin-releases")
    assert m["product"] == "AFMI Smart Admin"
    assert m["url"] == "https://github.com/saidsocial5-droid/afmi-smart-admin-releases/releases/download/v9.9.9/AFMI_Smart_Admin_Setup_9.9.9.exe"
    assert m["sha256"] == hashlib.sha256(b"installateur").hexdigest() and m["size"] == 12
    json.dumps(m)


def test_notes_from_changelog(tmp_path):
    cl = tmp_path / "CHANGELOG.md"
    cl.write_text("# Journal\n\n## [3.0.0] — 01/01/2027 — Grande version\n\n### Ajouté\n- **Module A** : détail.\n- Module B.\n\n"
                  "## [2.0.0] — x — Ancienne\n- Vieux.\n", encoding="utf-8")
    notes = mm.release_notes("3.0.0", cl)
    assert notes.startswith("Grande version.") and "Module A" in notes and "Module B" in notes and "Vieux" not in notes
    assert mm.release_notes("4.0.0", cl) == "Version 4.0.0."


def test_current_version_has_notes():
    import re
    version = re.search(r"set VERSION=([\d.]+)", (ROOT / "build_installer.bat").read_text()).group(1)
    assert mm.release_notes(version) != f"Version {version}.", "Ajoutez la section de la version au CHANGELOG avant publication"
