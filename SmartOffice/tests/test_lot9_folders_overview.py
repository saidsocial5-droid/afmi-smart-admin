"""Lot 9 — classement des documents (arborescence, dossiers, copie locale), vue 360° du projet, recherche unifiée."""
import asyncio
from pathlib import Path

from backend.core import unified_db
from backend.tools import overview
from backend.tools.ged import folders, service as ged
from backend.tools.meetings import service as meetings
from tests.test_lot5_reports import unified  # noqa: F401


def _pdf(text: str) -> bytes:
    import pymupdf
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), text)
    return d.tobytes()


def test_local_subfolders_follow_desktop_structure():
    assert folders.local_subfolder("Convention", "2026-05-02") == Path("Documents Généraux & Conventions")
    assert folders.local_subfolder("Procès-verbal", "2026-05-02") == Path("Année 2026") / folders.QUARTERS[1] / "Comptes Rendus (CR)"
    assert folders.local_subfolder("Rapport financier", "2026-11-30") == Path("Année 2026") / folders.QUARTERS[3] / "Rapports Financiers"
    assert folders.local_subfolder("Correspondance", "2026-01-15") == Path("Année 2026") / folders.QUARTERS[0]


def test_import_copies_into_local_folders_and_tree(unified, tmp_path):
    unified_db.set_setting("ged.local_root", str(tmp_path / "AFMI_Projets"))
    res = asyncio.run(ged.import_document(1, _pdf("Proces-verbal de la reunion du comite. Le comite decide."), "PV_comite.pdf",
                                          title="PV comité mars", doc_type="Procès-verbal"))
    local = Path(res["local_copy"])
    assert local.exists() and "Comptes Rendus (CR)" in local.parts and local.parts[-5].startswith("P1 - ")
    with unified_db.connect() as conn:
        assert conn.execute("SELECT LocalFolderPath FROM Projects WHERE Id = 1").fetchone()[0].endswith("P1 - Projet 1")
    assert folders.mirror_document(res["document"]["id"]) == str(local)          # pas de doublon
    tree = folders.tree()
    year = tree["years"][0]
    assert year["projects"][0]["types"] == [{"name": "Procès-verbal", "count": 1}]
    f = folders.create_folder({"name": "Correspondances: bailleur", "project_id": 1, "year": int(year["year"])})
    assert f["name"] == "Correspondances bailleur"                                # caractères interdits retirés
    ged.update(res["document"]["id"], {"folder_id": f["id"]})
    assert [d["id"] for d in folders.documents(folder_id=f["id"])] == [res["document"]["id"]]
    folders.delete_folder(f["id"])
    assert folders.documents(folder_id=f["id"]) == [] and ged.get(res["document"]["id"])   # le document reste


def test_no_local_copy_in_demo(unified, tmp_path, monkeypatch):
    unified_db.set_setting("ged.local_root", str(tmp_path / "AFMI_Projets"))
    monkeypatch.setenv("AFMI_DEMO", "1")
    res = asyncio.run(ged.import_document(1, _pdf("Facture numero 12"), "facture.pdf", doc_type="Facture"))
    assert res["local_copy"] is None and not (tmp_path / "AFMI_Projets").exists()


def test_project_overview_and_unified_search(unified, client):
    meetings.save({"kind": "COPIL", "title": "Comité de pilotage cèdre", "date": "2026-03-10", "project_id": 1,
                   "decisions": [{"text": "Valider la plantation de printemps"}], "actions": [{"text": "Commander les plants", "due_date": "2026-01-01"}]})
    o = overview.project_overview(1)
    assert o["project"]["code"] == "P1" and o["meetings"]["count"] == 1 and o["meetings"]["open_actions"][0]["late"]
    assert any(a["code"] == "MEETING_ACTION_LATE" for a in o["alerts"])
    assert o["budget"]["planned"] == 200000 and o["treasury"]                     # compte lié au projet (scénario partagé)
    r = client.get("/api/search", params={"q": "plantation"}).json()
    assert r["meetings"][0]["title"] == "Comité de pilotage cèdre"
    assert client.get("/api/search", params={"q": "Subvention"}).json()["operations"]
    assert client.get("/api/overview/project/999").status_code == 404
    assert client.get("/api/ged/tree").status_code == 200
