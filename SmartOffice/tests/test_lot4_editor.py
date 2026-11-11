import io
import json
import sqlite3
from datetime import datetime

import pytest
from PIL import Image

from backend.config.settings import settings
from backend.core import unified_db
from backend.tools.editor import assistant, charts
from tests.unified_db_fixture import create_unified_db


@pytest.fixture()
def unified(tmp_path, monkeypatch):
    path = create_unified_db(tmp_path / "database.db")
    monkeypatch.setenv(unified_db.DESKTOP_DB_ENV, str(path))
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    logo = tmp_path / "logo_bailleur.png"
    Image.new("RGB", (40, 20), "blue").save(logo)
    secret = tmp_path / "secret.txt"
    secret.write_text("confidentiel")
    conn = sqlite3.connect(str(path))
    conn.executescript(f"""
        INSERT INTO Funders (Id, Name, PrimaryColor, LogoPath, LegalMentions, HeaderText, FooterText)
        VALUES (1, 'Fonds Vert', '#0055A4', '{logo}', 'Ce projet est financé par le Fonds Vert.', '', 'Fonds Vert — programme forêts');
        INSERT INTO Funders (Id, Name, PrimaryColor, LogoPath, LegalMentions, HeaderText, FooterText)
        VALUES (2, 'Autre', '#000000', '{secret}', '', '', '');
        INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal,
                              LessonsLearned, LocalFolderPath, Currency, IsDeleted, FunderId)
        VALUES (1, 'Reboisement du cèdre', 'P-CEDRE', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0, 1);
        INSERT INTO Tasks (Id, ProjectId, Name, Description, Assignee, ProgressPercentage, Status, Budget, Cost, Predecessors)
        VALUES (1, 1, 'Plantation', '', '', 50, 'En cours', 0, 0, '');
        INSERT INTO ActivityReports (Id, Title, ActivityDate, Location, ParticipantsCount, Narrative, Difficulties, Recommendations, Status, ProjectTaskId)
        VALUES (1, 'Journée de plantation', '2026-03-12 00:00:00', 'Azrou', 45, '', '', '', 'Validé', 1);
        INSERT INTO Indicators (Id, Name, Description, TargetValue, CurrentValue, Unit, ProjectId)
        VALUES (1, 'Plants mis en terre', '', 10000, 6500, 'plants', 1);
        INSERT INTO BankAccounts (Id, Kind, Purpose, BankName, Branch, Title, Rib, Currency, OpeningBalanceMinor, OpeningDate, Status, Notes, IsDeleted)
        VALUES (1, 'Bank', 'Project', 'BP', '', 'Compte projet', NULL, 'MAD', 0, '2026-01-01', 'Active', '', 0);
        INSERT INTO BudgetLines (Id, ProjectId, Code, Label, CategoryId, PlannedMinor, Currency, IsDeleted)
        VALUES (1, 1, '2.1', 'Plants', 7, 5000000, 'MAD', 0);
        INSERT INTO Operations (Id, BankAccountId, OperationDate, Label, Reference, ThirdParty, Direction, Nature, AmountMinor, Currency,
                                AmountMadMinor, Status, ValidatedBy, Notes, IsDeleted)
        VALUES (1, 1, '2026-03-01', 'Achat plants', '', '', 'Debit', 'Expense', 1250000, 'MAD', 1250000, 'Validated', 'x', '', 0);
        INSERT INTO OperationAllocations (OperationId, ProjectId, BudgetLineId, CategoryId, AmountMinor) VALUES (1, 1, 1, 7, 1250000);
    """)
    conn.commit()
    conn.close()
    return path


def test_chart_inheritance_association_funder_project(client, unified):
    charts_list = client.get("/api/charts").json()
    assert charts_list[0]["scope"] == "Association"                        # créée automatiquement

    eff = client.get("/api/charts/effective?project_id=1").json()
    assert eff["chain"] == ["Valeurs par défaut", "Charte AFMI", "Fiche bailleur : Fonds Vert"]
    assert eff["style"]["colors"]["primary"] == "#0055A4"                  # couleur de la fiche bailleur
    assert eff["style"]["mentions"] == ["Ce projet est financé par le Fonds Vert."]
    assert eff["style"]["footer"]["page_numbers"] is True                  # défaut conservé

    client.post("/api/charts", json={"name": "Charte Fonds Vert", "scope": "Funder", "funder_id": 1, "style": {
        "fonts": {"body": "Arial"}, "mentions": ["Avec le soutien du Fonds Vert"],
        "logos": [{"file_id": 7, "position": "footer-right", "height_mm": 10}]}})
    client.post("/api/charts", json={"name": "Charte Cèdre", "scope": "Project", "project_id": 1, "style": {
        "colors": {"secondary": "#AA0000"}, "logos": [{"file_id": 8, "position": "header-right"}], "margins_mm": {"top": 30}}})
    eff = client.get("/api/charts/effective?project_id=1").json()
    s = eff["style"]
    assert eff["chain"][-2:] == ["Charte Fonds Vert", "Charte Cèdre"]
    assert s["colors"] == {"primary": "#0055A4", "secondary": "#AA0000", "text": "#1F2937", "muted": "#6B7280"}
    assert s["fonts"]["body"] == "Arial" and s["fonts"]["size_pt"] == 11
    assert s["margins_mm"]["top"] == 30 and s["margins_mm"]["left"] == 20
    assert {l["position"]: l["file_id"] for l in s["logos"]} == {"header-right": 8, "footer-right": 7}
    assert s["mentions"] == ["Ce projet est financé par le Fonds Vert.", "Avec le soutien du Fonds Vert"]

    assert client.post("/api/charts", json={"name": "Doublon", "scope": "Funder", "funder_id": 1, "style": {}}).status_code == 400
    assert client.post("/api/charts", json={"name": "X", "scope": "Project", "project_id": 1, "style": {"logos": [{"file_id": 1, "position": "plafond"}]}}).status_code == 400
    assert client.delete(f"/api/charts/{charts_list[0]['id']}").status_code == 400


def test_merge_rules():
    base = {"a": {"x": 1, "y": 2}, "mentions": ["m1"], "logos": [{"file_id": 1, "position": "header-left"}]}
    out = charts.merge(base, {"a": {"y": 3}, "mentions": ["m1", "m2"], "logos": [{"file_id": None, "position": "header-left"}]})
    assert out == {"a": {"x": 1, "y": 3}, "mentions": ["m1", "m2"], "logos": []}   # logo retiré explicitement


def test_templates_documents_versions_comments(client, unified):
    content = {"type": "doc", "content": [{"type": "heading", "attrs": {"level": 1}, "content": [{"type": "text", "text": "Rapport"}]}]}
    t = client.post("/api/templates", json={"name": "Rapport trimestriel", "kind": "rapport", "content": content, "layout": {"margins_mm": {"top": 30}}}).json()
    dup = client.post(f"/api/templates/{t['id']}/duplicate").json()
    assert dup["name"] == "Rapport trimestriel (copie)" and dup["content"] == content
    assert len(client.get("/api/templates").json()) == 2

    doc = client.post("/api/documents", json={"title": "Rapport T1", "template_id": t["id"], "project_id": 1}).json()
    assert doc["content"] == content and doc["layout"] == {"margins_mm": {"top": 30}} and doc["version"] == 0

    edited = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x" * 5000}]}]}
    doc = client.put(f"/api/documents/{doc['id']}", json={"content": edited, "version_note": "Première relecture"}).json()
    assert doc["version"] == 1
    doc = client.put(f"/api/documents/{doc['id']}", json={"title": "Rapport T1 — final"}).json()
    versions = client.get(f"/api/documents/{doc['id']}/versions").json()
    assert [v["number"] for v in versions] == [1]

    client.put(f"/api/documents/{doc['id']}", json={"content": content})
    restored = client.post(f"/api/documents/{doc['id']}/versions/{versions[0]['id']}/restore").json()
    assert restored["content"] == edited
    assert [v["number"] for v in client.get(f"/api/documents/{doc['id']}/versions").json()] == [3, 2, 1]   # l'état remplacé est conservé

    c = client.post(f"/api/documents/{doc['id']}/comments", json={"text": "Chiffre à vérifier", "anchor_id": "c1", "quoted": "6 500 plants"}).json()
    assert c["author"] and not c["resolved"]
    assert client.post(f"/api/documents/{doc['id']}/comments/{c['id']}/resolve").json()["resolved"] is True
    assert client.post(f"/api/documents/{doc['id']}/comments", json={"text": " "}).status_code == 400

    db = sqlite3.connect(str(unified))
    long_entries = db.execute("SELECT ChangesJson FROM AuditEntries WHERE EntityType = 'EditorDocument'").fetchall()
    assert any("[texte de" in r[0] for r in long_entries)                  # contenu long résumé dans le journal
    db.row_factory = sqlite3.Row
    assert unified_db.find_first_tampered_audit_entry(db) is None


def test_dynamic_blocks_come_from_the_data(client, unified):
    budget = client.get("/api/editor/blocks/budget?project_id=1").json()
    assert budget["rows"][0]["realized_mad"] == 1_250_000 and budget["rows"][0]["rate"] == 25.0
    assert budget["total"]["gap"] == 3_750_000
    ind = client.get("/api/editor/blocks/indicators?project_id=1").json()["rows"][0]
    assert ind["rate"] == 65.0
    act = client.get("/api/editor/blocks/activities?project_id=1&date_from=2026-03-01&date_to=2026-03-31").json()
    assert act["total_participants"] == 45 and act["rows"][0]["task"] == "Plantation"
    assert client.get("/api/editor/blocks/activities?project_id=1&date_from=2026-04-01").json()["rows"] == []
    chart = client.get("/api/editor/blocks/chart?project_id=1&chart=budget").json()
    assert chart["series"] == [{"label": "2.1 Plants", "planned": 50000.0, "actual": 12500.0}]
    fields = client.get("/api/editor/fields?project_id=1").json()
    assert fields["project_name"] == "Reboisement du cèdre" and fields["funder_name"] == "Fonds Vert"
    assert client.get("/api/editor/blocks/inconnu").status_code == 404


def _jpeg_with_exif(color, taken: str, gps=None) -> bytes:
    img = Image.new("RGB", (1200, 800), color)
    exif = Image.Exif()
    exif[306] = taken
    exif.get_ifd(0x8769)[36867] = taken
    if gps:
        exif.get_ifd(0x8825).update(gps)
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_photos_exif_consent_selection_and_captions(client, unified):
    gps = {1: "N", 2: (33.0, 32.0, 24.0), 3: "W", 4: (5.0, 13.0, 12.0)}
    files = [("files", ("p1.jpg", _jpeg_with_exif("green", "2026:03:12 10:00:00", gps))),
             ("files", ("p2.jpg", _jpeg_with_exif("brown", "2026:03:12 11:00:00"))),
             ("files", ("p3.jpg", _jpeg_with_exif("gray", "2026:03:20 09:30:00"))),
             ("files", ("doc.pdf", b"%PDF"))]
    res = client.post("/api/photos/upload", data={"project_id": "1", "credit": "AFMI", "consent": "true"}, files=files).json()["results"]
    photos = [r["photo"] for r in res if "photo" in r]
    assert len(photos) == 3 and "error" in res[3]
    p1 = photos[0]
    assert p1["taken_at"] == "2026-03-12 10:00:00" and p1["latitude"] == pytest.approx(33.54) and p1["longitude"] == pytest.approx(-5.22)
    assert client.get(p1["url"]).headers["content-type"] == "image/jpeg"

    again = client.post("/api/photos/upload", data={"project_id": "1"}, files=[("files", ("p1.jpg", _jpeg_with_exif("green", "2026:03:12 10:00:00", gps)))]).json()
    assert "déjà importée" in again["results"][0]["error"]

    client.put(f"/api/photos/{photos[2]['id']}", json={"consent": False})
    sel = client.get("/api/editor/blocks/gallery?project_id=1&date_from=2026-03-01&date_to=2026-03-31&limit=6").json()["photos"]
    assert [p["id"] for p in sel] == [photos[0]["id"], photos[1]["id"]]       # sans consentement : jamais sélectionnée

    updated = client.put(f"/api/photos/{photos[1]['id']}", json={"caption": "Plantation de cèdres avec les élèves"}).json()
    assert updated["caption_validated"] is True
    sel = client.get("/api/editor/blocks/gallery?project_id=1&limit=1").json()["photos"]
    assert sel[0]["id"] == photos[1]["id"]                                      # légende validée en priorité
    chosen = client.get(f"/api/editor/blocks/gallery?photo_ids={photos[1]['id']},{photos[0]['id']}&project_id=1").json()["photos"]
    assert [p["id"] for p in chosen] == [photos[1]["id"], photos[0]["id"]]       # ordre choisi dans l'éditeur

    # Pas de modèle de vision disponible pendant les tests : aucune légende inventée.
    sug = client.post(f"/api/photos/{photos[0]['id']}/suggest-caption").json()
    assert sug["engine"] == "heuristic" and sug["photo"]["suggested_caption"] == ""


def test_images_and_logos_are_served_safely(client, unified):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "PNG")
    up = client.post("/api/files/images", files={"file": ("logo.png", buf.getvalue())}).json()
    assert client.get(up["url"]).headers["content-type"] == "image/png"
    assert client.post("/api/files/images", files={"file": ("x.exe", b"MZ")}).status_code == 400
    assert client.get("/api/funders/1/logo").status_code == 200
    assert client.get("/api/funders/2/logo").status_code == 404                  # chemin non image : jamais servi


def test_assistant_offline_and_number_check(client, unified):
    r = client.post("/api/editor/assistant", json={"action": "complete", "instruction": "Résultats", "project_id": 1}).json()
    assert r["offline"] is True and r["facts"]["indicateurs"][0]["current"] == 6500
    assert client.post("/api/editor/assistant", json={"action": "pirater", "text": "x"}).status_code == 400
    facts = {"indicateurs": [{"current": 6500, "target": 10000}]}
    assert assistant.numbers_not_in_facts("6 500 plants sur 10000 prévus, soit 65 %", facts) == ["65"]
