import io
import sqlite3
from datetime import date, timedelta

import pytest

from backend.config.settings import settings
from backend.core import unified_db
from backend.core.llm_router import llm_router
from backend.tools.ged import analyze, textract
from tests.unified_db_fixture import create_unified_db

try:
    import pymupdf as fitz
except ImportError:
    import fitz

CONVENTION = """CONVENTION DE FINANCEMENT N° FV-2026-07
Entre : le Fonds Vert, ci-après dénommé « le Bailleur », et l'Association Forêt Modèle d'Ifrane, ci-après dénommée « l'Association ».
Article 3 – Durée. La présente convention prend effet à compter du 01/01/2026 pour une durée de 18 mois.
Article 4 – Montant. Le Bailleur accorde une subvention de 1 200 000 MAD versée en deux tranches.
Article 7 – Rapports. L'Association transmettra des rapports narratifs et financiers semestriels dans les 30 jours suivant la fin de chaque semestre.
Un rapport final sera remis au plus tard 60 jours après la fin du projet.
Article 9 – Visibilité. Le logo du Bailleur figurera sur tous les supports de communication et les panneaux de chantier.
Fait à Ifrane, le 15 décembre 2025."""


def _pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 560, 800), text, fontsize=10)
    return doc.tobytes()


def _docx(paragraphs) -> bytes:
    from docx import Document
    d = Document()
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.fixture()
def unified(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal, LessonsLearned,
                              LocalFolderPath, Currency, IsDeleted, TargetStartDate, TargetEndDate)
        VALUES (1, 'Reboisement', 'P1', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0, '2026-01-01 00:00:00', '2027-06-30 00:00:00'),
               (2, 'Autre projet', 'P2', '', '', '', '', '', 'Initiation', 'Basse', 0, '', '', 'MAD', 0, NULL, NULL);
    """)
    conn.commit()
    conn.close()
    return path


def _upload(client, name, data, project_id=1, **form):
    return client.post("/api/ged/documents", data={"project_id": str(project_id), **form}, files=[("files", (name, data))]).json()["results"][0]


def test_convention_is_classified_analysed_and_obligations_proposed(client, unified):
    pdf = _pdf(CONVENTION)
    r = _upload(client, "Convention_FV_2026.pdf", pdf)
    d = r["document"]
    assert d["doc_type"] == "Convention" and d["phase"] == "Contractualisation" and d["confidence"] > 50
    assert d["signature_date"] == "2025-12-15" and d["end_date"] == "2027-06-30" and d["has_file"] and d["indexed"]
    assert d["metadata"]["max_amount"]["value"] == 1200000 and d["metadata"]["duration_months"] == 18
    assert any("Fonds Vert" in p for p in d["metadata"]["parties"])
    obls = client.get("/api/ged/obligations?project_id=1").json()
    assert [o["due"] for o in obls] == ["2026-07-30", "2027-01-30", "2027-07-30", "2027-08-29"]
    assert all(o["status"] == "Proposée" and "semestriels" in o["excerpt"] or o["title"] == "Rapport final" for o in obls)
    assert "déjà dans la GED" in _upload(client, "copie.pdf", pdf)["error"]          # même fichier (même empreinte)
    alerts = client.get("/api/ged/alerts?project_id=1").json()
    assert any(a["code"] == "OBLIGATIONS_TO_CONFIRM" for a in alerts)


def test_confirmed_obligations_drive_alerts_and_reports_close_them(client, unified):
    soon = (date.today() + timedelta(days=10)).isoformat()
    late = (date.today() - timedelta(days=5)).isoformat()
    o1 = client.post("/api/ged/obligations", json={"project_id": 1, "title": "Rapport financier S1", "kind": "Rapport financier", "due": late}).json()
    client.post("/api/ged/obligations", json={"project_id": 1, "title": "Rapport narratif S1", "kind": "Rapport narratif", "due": soon})
    codes = {a["code"] for a in client.get("/api/ged/alerts?project_id=1").json()}
    assert {"REPORT_LATE", "REPORT_DUE"} <= codes

    rep = _upload(client, "Rapport_financier_S1.docx", _docx(["RAPPORT FINANCIER — premier semestre 2026",
                                                             "État des dépenses et taux de consommation du budget.", "Exécution budgétaire : 45 %."]))
    assert rep["document"]["doc_type"] == "Rapport financier" and rep["document"]["phase"] == "Suivi"
    obls = {o["id"]: o for o in client.get("/api/ged/obligations?project_id=1").json()}
    assert obls[o1["id"]]["status"] == "Remise" and obls[o1["id"]]["delivered_document_id"] == rep["document"]["id"]
    assert "REPORT_LATE" not in {a["code"] for a in client.get("/api/ged/alerts?project_id=1").json()}


def test_full_text_search_question_answering_and_soft_delete(client, unified):
    doc = _upload(client, "Convention.pdf", _pdf(CONVENTION))["document"]
    _upload(client, "PV_comite.txt", "Procès-verbal du comité de pilotage. Étaient présents : le maire et le directeur. Ordre du jour : plantation.".encode(), project_id=2)
    res = client.get("/api/ged/search?q=visibilite logo&project_id=1").json()          # sans accents → trouve « Visibilité »
    assert res["mode"] == "plein texte" and res["results"][0]["document_id"] == doc["id"] and "[" in res["results"][0]["snippet"]
    assert client.get("/api/ged/search?q=comite pilotage&project_id=1").json()["results"] == []      # filtré par projet
    ans = client.post("/api/ged/ask", json={"question": "Quand les rapports semestriels doivent-ils être transmis ?", "project_id": 1}).json()
    assert ans["engine"] == "heuristic" and ans["sources"][0]["title"] == "Convention" and "[1]" in ans["answer"]
    client.put(f"/api/ged/documents/{doc['id']}", json={"doc_type": "Avenant", "phase": "Mise en œuvre"})
    assert client.get(f"/api/ged/documents/{doc['id']}").json()["confidence"] == 100
    client.delete(f"/api/ged/documents/{doc['id']}")
    assert client.get("/api/ged/search?q=visibilite").json()["results"] == []
    assert client.get(f"/api/ged/documents/{doc['id']}/file").status_code == 400


def test_timeline_phase_expected_documents_and_milestones(client, unified):
    _upload(client, "Convention.pdf", _pdf(CONVENTION))
    m = client.post("/api/ged/milestones", json={"project_id": 1, "title": "Comité de pilotage n° 1", "date": "2026-03-15", "phase": "Mise en œuvre"}).json()
    tl = client.get("/api/ged/timeline/1").json()
    assert tl["phase"] == "Mise en œuvre"
    lanes = {i["lane"] for i in tl["items"]}
    assert {"Projet", "Jalons", "Rapports dus", "Documents"} <= lanes
    assert tl["items"] == sorted(tl["items"], key=lambda i: i["date"])
    missing = [e["doc_type"] for e in tl["expected"] if e["reached"] and e["count"] == 0]
    assert "Budget" in missing and "Convention" not in missing
    assert any(a["code"] == "MISSING_DOCUMENT" and "Budget" in a["message"] for a in client.get("/api/ged/alerts?project_id=1").json())
    assert client.post("/api/ged/milestones", json={"project_id": 1, "title": "x", "date": "2026-01-01", "phase": "Galaxie"}).status_code == 400
    client.delete(f"/api/ged/milestones/{m['id']}")
    assert "Jalons" not in {i["lane"] for i in client.get("/api/ged/timeline/1").json()["items"]}


def test_existing_desktop_documents_are_reindexed(client, unified):
    db = sqlite3.connect(str(unified))
    db.execute("INSERT INTO Documents (ProjectId, Title, Category, DocumentPhase, Tags, IsKeyReference, DocumentVersion, DonorName, DocumentReference, "
               "ApprovedGrantAmount, FilePath, OriginalFileName, FileExtension, FileSize, Notes, ExtractedSummary, FullExtractedText, KeyInsights, "
               "UploadedDate, DocType, LifecyclePhase, ClassificationConfidence, MetadataJson, Language, IsDeleted) "
               "VALUES (1, 'Ancien rapport', 'Dossier Projet', 'Exécution', '', 1, '', '', '', 0, 'C:/introuvable.pdf', '', '', 0, '', 'Rapport 2025', "
               "'Rapport d''avancement : 3 ateliers de sensibilisation réalisés à Azrou.', '', '2025-06-01', 'Document de projet', 'Mise en œuvre', 100, '{}', '', 0)")
    db.commit()
    r = client.post("/api/ged/reindex?project_id=1").json()
    assert r["indexed"] == 1
    assert client.get("/api/ged/search?q=ateliers azrou").json()["results"][0]["title"] == "Ancien rapport"


def test_semantic_search_is_used_when_embeddings_are_available(client, unified, monkeypatch):
    vocab = ["rapport", "semestriel", "visibilite", "logo", "montant", "subvention", "duree", "mois"]

    async def fake_embed(texts):
        from backend.tools.statements.templates import normalize
        return [[float(normalize(t).count(w)) + 0.01 for w in vocab] for t in texts], "test:bow"
    monkeypatch.setattr(llm_router, "embed", fake_embed)
    _upload(client, "Convention.pdf", _pdf(CONVENTION))
    res = client.get("/api/ged/search?q=quelle subvention&project_id=1").json()
    assert res["mode"].startswith("hybride") and res["results"]


def test_text_extraction_formats_and_analysis_helpers():
    pages, engine = textract.extract(_docx(["Termes de référence", "Objet de la mission : diagnostic."]), "tdr.docx")
    assert engine == "docx" and "Objet de la mission" in pages[0][1]
    with pytest.raises(textract.ExtractionError):
        textract.extract(b"x", "ancien.doc")
    assert analyze.classify("TdR consultant", "Termes de référence. Objet de la mission. Profil du consultant. Livrables attendus.")[0] == "Termes de référence"
    assert analyze.classify("Note", "texte sans rapport")[0] == "Autre"
    assert analyze.dates_in("Signée le 1er mars 2026 et le 15/04/2026") == ["2026-03-01", "2026-04-15"]
    assert analyze.language("التقرير السنوي للجمعية حول الأنشطة") == "ar"


def test_institutional_memory_includes_key_documents(client, unified):
    _upload(client, "Convention.pdf", _pdf(CONVENTION))
    from backend.core.base_agent import BaseAgent
    lines = BaseAgent._key_documents_context()
    assert any("Convention" in l and "[P1]" in l for l in lines)
