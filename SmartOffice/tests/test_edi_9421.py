import io
import zipfile
from pathlib import Path

from lxml import etree

from backend.config.settings import settings

YEAR = 2024


def _setup_year(client):
    for m, (name, status) in enumerate([("Alaoui Fatima", "marie"), ("Benali Youssef", "celibataire")], start=1):
        r = client.post("/api/payroll/employees", json={
            "matricule": f"EDI{m}", "full_name": name, "cin": f"D{m}00000", "cnss_number": f"11111111{m}",
            "hire_date": "2015-01-01", "dependents": 2 if status == "marie" else 0, "marital_status": status,
            "base_salary": 9000 + m * 1000})
        assert r.status_code == 200, r.text
    for month in ("01", "02"):
        assert client.post(f"/api/payroll/runs/{YEAR}-{month}", json={}).json()["computed"] >= 2
        client.post(f"/api/payroll/periods/{YEAR}-{month}/validate")


def _fill_config(client, ref_taux="CODE_TAUX_TEST"):
    cfg = client.get("/api/payroll/edi/config").json()["config"]
    cfg["employer"].update({"identifiant_fiscal": "40291845", "commune_code": "COMMUNE_TEST",
                            "numero_cnss": "1234567"})
    cfg["codes"]["ref_taux_permanent"] = ref_taux
    cfg["codes"]["situation_familiale"].update({"celibataire": "C_TEST", "marie": "M"})
    cfg["codes"]["moyen_paiement"]["teleservice"] = "TS_TEST"
    assert client.put("/api/payroll/edi/config", json=cfg).status_code == 200


def test_export_blocked_until_annex_codes_are_filled(client):
    _setup_year(client)
    cfg = client.get("/api/payroll/edi/config").json()["config"]
    cfg["codes"]["ref_taux_permanent"] = ""
    client.put("/api/payroll/edi/config", json=cfg)
    pre = client.get(f"/api/payroll/declarations/9421/{YEAR}/edi/preflight").json()
    assert any("refTaux" in e for e in pre["errors"])
    assert client.post(f"/api/payroll/declarations/9421/{YEAR}/edi").status_code == 400


def test_edi_file_structure_and_totals(client):
    _fill_config(client)
    client.post("/api/payroll/ir-payments", json={"period": f"{YEAR}-01", "amount": 1500.0,
                                                  "payment_date": f"{YEAR}-02-20", "reference": "REF1",
                                                  "receipt_number": "Q1", "payment_method": "teleservice"})
    pre = client.get(f"/api/payroll/declarations/9421/{YEAR}/edi/preflight").json()
    assert pre["errors"] == []
    assert any(f"{YEAR}-02" in w for w in pre["warnings"])   # February IR payment not recorded

    out = client.post(f"/api/payroll/declarations/9421/{YEAR}/edi").json()
    assert out["filename"].endswith(".zip")
    assert out["schema_validated"] is False and out["schema_file"] is None
    with zipfile.ZipFile(Path(settings.exports_dir) / out["filename"]) as z:
        [name] = z.namelist()
        assert name.endswith(".xml")
        root = etree.fromstring(z.read(name))

    assert root.tag == "TraitementEtSalaire"
    assert root.findtext("identifiantFiscal") == "40291845"
    assert root.findtext("annee") == str(YEAR)
    assert root.findtext("commune/code") == "COMMUNE_TEST"
    perms = root.findall("listPersonnelPermanent/PersonnelPermanent")
    assert {p.findtext("numCNI") for p in perms} >= {"D100000", "D200000"}
    fatima = next(p for p in perms if p.findtext("numCNI") == "D100000")
    assert fatima.findtext("nom") == "Alaoui" and fatima.findtext("prenom") == "Fatima"
    assert fatima.findtext("refSituationFamiliale/code") == "M"
    assert fatima.findtext("refTaux/code") == "CODE_TAUX_TEST"
    assert fatima.findtext("periode") == "52"   # 2 months x 26 days
    # Identity checked by the DGI: brut + avantages - exonéré = brut imposable
    brut = float(fatima.findtext("mtBrutTraitementSalaire"))
    assert abs(brut + float(fatima.findtext("mtAvantages")) - float(fatima.findtext("mtExonere"))
               - float(fatima.findtext("mtRevenuBrutImposable"))) < 0.01
    total_ir = sum(float(p.findtext("irPreleve")) for p in perms)
    assert abs(float(root.findtext("totalMtIrPrelevePP")) - total_ir) < 0.01
    v = root.find("listVersements/VersementTraitementSalaire")
    assert v.findtext("mois") == "1"
    assert v.findtext("listDetailPaiement/DetailPaiementTraitementSalaire/refMoyenPaiement/code") == "TS_TEST"


TEST_XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="TraitementEtSalaire">
    <xs:complexType><xs:sequence>
      <xs:element name="identifiantFiscal" type="xs:string"/>
      <xs:any minOccurs="0" maxOccurs="unbounded" processContents="skip"/>
    </xs:sequence></xs:complexType>
  </xs:element>
</xs:schema>"""

STRICT_XSD = TEST_XSD.replace('name="identifiantFiscal" type="xs:string"', 'name="champInexistant" type="xs:string"')


def test_schema_in_designated_folder_is_enforced(client):
    """Test fixture schemas only: the official DGI XSD is dropped by the user in edi_schemas/."""
    _fill_config(client)
    schema_file = Path(settings.edi_schemas_dir) / "traitementSalaire.xsd"
    try:
        schema_file.write_text(TEST_XSD, encoding="utf-8")
        out = client.post(f"/api/payroll/declarations/9421/{YEAR}/edi").json()
        assert out["schema_validated"] is True and out["schema_file"] == "traitementSalaire.xsd"

        schema_file.write_text(STRICT_XSD, encoding="utf-8")
        r = client.post(f"/api/payroll/declarations/9421/{YEAR}/edi")
        assert r.status_code == 400 and "non conforme" in r.json()["detail"]
    finally:
        schema_file.unlink(missing_ok=True)


def test_ir_payment_validation(client):
    bad = client.post("/api/payroll/ir-payments", json={"period": f"{YEAR}-13", "amount": 10, "payment_date": "2024-01-01"})
    assert bad.status_code == 422
    assert client.post("/api/payroll/ir-payments", json={"period": f"{YEAR}-03", "amount": 0,
                                                         "payment_date": "2024-04-01"}).status_code == 422


def test_marital_status_column_added_to_existing_tables():
    from sqlalchemy import create_engine, inspect, text
    from backend.core import database
    legacy = create_engine(f"sqlite:///{Path(settings.data_dir) / 'legacy_test.db'}")
    with legacy.begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY, matricule VARCHAR(30))"))
    original = database.engine
    try:
        database.engine = legacy
        database._add_missing_columns()
        database._add_missing_columns()   # idempotent
    finally:
        database.engine = original
    assert "marital_status" in {c["name"] for c in inspect(legacy).get_columns("employees")}
