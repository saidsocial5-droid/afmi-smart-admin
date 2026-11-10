"""
EDI file of the état 9421 (Simpl-IR « Déclaration des traitements et salaires »).

Element names and order follow the DGI EDI specification (cahier des charges DTS v2.0, January 2015):
root <TraitementEtSalaire>, employer header, totals, <listPersonnelPermanent>, <listPersonnelOccasionnel>,
<listStagiaires>, <listBeneficiaires>, <listBeneficiairesPlanEpargne>, <listVersements>.

Reference codes (rate, marital status, commune, payment method) come from the DGI « Annexe 2 – Codification
Référentiel » and are read from edi_9421_config.json: a missing code blocks the export instead of being guessed.
When the official XSD is placed in settings.edi_schemas_dir, every file is validated against it before export.
Simpl-IR only accepts the XML compressed as .zip, so the export is a zip archive.
"""
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree

from backend.config.settings import settings

MAX_XML_BYTES = 15 * 1024 * 1024   # limit stated in the DGI specification
XSI = "http://www.w3.org/2001/XMLSchema-instance"


def load_config() -> Dict[str, Any]:
    with open(settings.edi_9421_config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data: Dict[str, Any]) -> None:
    with open(settings.edi_9421_config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def employer_values(config: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, str]:
    """Config values win; empty ones fall back to the institutional profile."""
    org = profile.get("organization", {})
    emp = dict(config.get("employer", {}))
    fallbacks = {"identifiant_fiscal": org.get("identifiant_fiscal"), "raison_sociale": org.get("name_fr"),
                 "adresse": org.get("headquarters")}
    for k, v in fallbacks.items():
        if not str(emp.get(k) or "").strip() and v:
            emp[k] = v
    return {k: str(v or "").strip() for k, v in emp.items()}


def _amount(value: Any) -> str:
    return f"{float(value or 0):.2f}"


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _split_name(full_name: str) -> Tuple[str, str]:
    """« Nom Prénom(s) » convention: first word is the family name."""
    parts = (full_name or "").strip().split()
    return (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (full_name.strip(), "")


def preflight(year: int, employees: List[Dict[str, Any]], payments: List[Dict[str, Any]],
              config: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Blocking errors (export refused) and warnings (export allowed)."""
    errors, warnings = [], []
    emp = employer_values(config, profile)
    codes = config.get("codes", {})

    if len(_digits(emp.get("identifiant_fiscal"))) < 7:
        errors.append("Identifiant fiscal (IF) de l'employeur manquant ou invalide.")
    if not emp.get("raison_sociale"):
        errors.append("Raison sociale de l'employeur manquante.")
    if not emp.get("commune_code"):
        errors.append("Code commune de l'employeur manquant (Annexe 2 – référentiel des communes).")
    if not codes.get("ref_taux_permanent"):
        errors.append("Code du taux applicable au personnel permanent (refTaux) manquant (Annexe 2).")
    if not employees:
        errors.append(f"Aucun bulletin de paie pour {year}.")

    family_codes = codes.get("situation_familiale", {})
    for e in employees:
        who = e.get("full_name") or e.get("matricule")
        if not e.get("cin"):
            errors.append(f"{who} : CIN manquante.")
        if not family_codes.get(e.get("marital_status") or "celibataire"):
            errors.append(f"{who} : code de situation familiale « {e.get('marital_status')} » non renseigné (Annexe 2).")
        if not _split_name(e.get("full_name", ""))[1]:
            warnings.append(f"{who} : prénom absent (format attendu « Nom Prénom »).")
        if e.get("drafts"):
            warnings.append(f"{who} : {e['drafts']} bulletin(s) non validé(s).")
        if not e.get("cnss_number"):
            warnings.append(f"{who} : n° CNSS manquant.")

    paid_months = {p["period"] for p in payments}
    ir_by_month = {}
    for e in employees:
        for month, ir in (e.get("ir_by_month") or {}).items():
            ir_by_month[month] = ir_by_month.get(month, 0.0) + ir
    for month, ir in sorted(ir_by_month.items()):
        if ir > 0 and month not in paid_months:
            warnings.append(f"Versement IR de {month} ({ir:,.2f} DH) non enregistré.")
    method_codes = codes.get("moyen_paiement", {})
    for p in payments:
        if not method_codes.get(p.get("payment_method")):
            errors.append(f"Versement {p['period']} : code du moyen de paiement « {p.get('payment_method')} » "
                          "non renseigné (Annexe 2).")
    return {"errors": errors, "warnings": warnings}


def build_xml(year: int, employees: List[Dict[str, Any]], payments: List[Dict[str, Any]],
              config: Dict[str, Any], profile: Dict[str, Any]) -> bytes:
    emp = employer_values(config, profile)
    codes = config["codes"]
    days_per_month = int(config.get("options", {}).get("days_per_month", 26))
    include_empty = bool(config.get("options", {}).get("include_empty_lists", True))

    root = etree.Element("TraitementEtSalaire", nsmap={"xsi": XSI})

    def add(parent, tag, value=None, keep_empty=False):
        if value is None or (str(value).strip() == "" and not keep_empty):
            return None
        el = etree.SubElement(parent, tag)
        el.text = str(value)
        return el

    def add_code(parent, tag, code):
        if code:
            etree.SubElement(etree.SubElement(parent, tag), "code").text = str(code)

    totals = {
        "brut_imposable": sum(e["salaire_brut_imposable"] for e in employees),
        "net_imposable": sum(e["salaire_net_imposable"] for e in employees),
        "deductions": sum(e["frais_professionnels"] + e["cotisations_sociales"]
                          + e["retraite_complementaire_salarie"] + e["interets_logement"] for e in employees),
        "ir": sum(e["ir_net"] for e in employees),
    }

    add(root, "identifiantFiscal", _digits(emp["identifiant_fiscal"]))
    add(root, "raisonSociale", emp["raison_sociale"])
    add(root, "exerciceFiscalDu", f"{year}-01-01")
    add(root, "exerciceFiscalAu", f"{year}-12-31")
    add(root, "annee", year)
    add_code(root, "commune", emp["commune_code"])
    add(root, "adresse", emp.get("adresse"))
    add(root, "numeroCNSS", emp.get("numero_cnss"))
    add(root, "numeroRC", emp.get("numero_rc"))
    add(root, "identifiantTP", emp.get("identifiant_tp"))
    add(root, "numeroFax", emp.get("numero_fax"))
    add(root, "numeroTelephone", emp.get("numero_telephone"))
    add(root, "email", emp.get("email"))
    add(root, "effectifTotal", len(employees))
    add(root, "nbrPersoPermanent", len(employees))
    add(root, "nbrPersoOccasionnel", 0)
    add(root, "nbrStagiaires", 0)
    add(root, "totalMtRevenuBrutImposablePP", _amount(totals["brut_imposable"]))
    add(root, "totalMtRevenuNetImposablePP", _amount(totals["net_imposable"]))
    add(root, "totalMtTotalDeductionPP", _amount(totals["deductions"]))
    add(root, "totalMtIrPrelevePP", _amount(totals["ir"]))
    add(root, "totalMtBrutSommesPO", _amount(0))
    add(root, "totalIrPrelevePO", _amount(0))
    add(root, "totalMtBrutTraitSalaireSTG", _amount(0))
    add(root, "totalMtBrutIndemnitesSTG", _amount(0))
    add(root, "totalMtRetenuesSTG", _amount(0))
    add(root, "totalMtRevenuNetImpSTG", _amount(0))
    add(root, "totalSommePayeRTS", _amount(0))
    add(root, "totalmtAnuuelRevenuSalarial", _amount(0))   # spelling as in the DGI specification
    add(root, "totalmtAbondement", _amount(0))
    add(root, "montantPermanent", _amount(totals["ir"]))
    add(root, "montantOccasionnel", _amount(0))
    add(root, "montantStagiaire", _amount(0))

    perm_list = etree.SubElement(root, "listPersonnelPermanent")
    family_codes = codes["situation_familiale"]
    max_persons = 6
    for e in employees:
        nom, prenom = _split_name(e["full_name"])
        p = etree.SubElement(perm_list, "PersonnelPermanent")
        add(p, "nom", nom)
        add(p, "prenom", prenom)
        add(p, "adressePersonnelle", e.get("address"))
        add(p, "numCNI", (e.get("cin") or "").upper())
        add(p, "numCNSS", e.get("cnss_number"))
        # Identity kept for the DGI checks: brut + avantages - exonéré = revenu brut imposable
        add(p, "mtBrutTraitementSalaire", _amount(e["salaire_brut_global"] - e["avantages_en_nature"]))
        add(p, "periode", e["months"] * days_per_month)
        add(p, "mtExonere", _amount(e["indemnites_exonerees"]))
        add(p, "mtEcheances", _amount(0))
        add(p, "nbrReductions", min(int(e.get("dependents") or 0), max_persons))
        add(p, "mtIndemnite", _amount(0))   # primes are already in the gross salary
        add(p, "mtAvantages", _amount(e["avantages_en_nature"]))
        add(p, "mtRevenuBrutImposable", _amount(e["salaire_brut_imposable"]))
        add(p, "mtFraisProfess", _amount(e["frais_professionnels"]))
        add(p, "mtCotisationAssur", _amount(e["cotisations_sociales"] + e["retraite_complementaire_salarie"]))
        add(p, "mtAutresRetenues", _amount(e["interets_logement"]))
        add(p, "mtRevenuNetImposable", _amount(e["salaire_net_imposable"]))
        add(p, "mtTotalDeduction", _amount(e["frais_professionnels"] + e["cotisations_sociales"]
                                           + e["retraite_complementaire_salarie"] + e["interets_logement"]))
        add(p, "irPreleve", _amount(e["ir_net"]))
        add(p, "casSportif", "false")
        add(p, "numMatricule", e.get("matricule"))
        add_code(p, "refSituationFamiliale", family_codes.get(e.get("marital_status") or "celibataire"))
        add_code(p, "refTaux", codes["ref_taux_permanent"])

    if include_empty:
        for tag in ("listPersonnelOccasionnel", "listStagiaires", "listBeneficiaires", "listBeneficiairesPlanEpargne"):
            etree.SubElement(root, tag)

    method_codes = codes["moyen_paiement"]
    vers_list = etree.SubElement(root, "listVersements")
    by_month: Dict[str, List[Dict[str, Any]]] = {}
    for pay in sorted(payments, key=lambda x: (x["period"], x["payment_date"])):
        by_month.setdefault(pay["period"], []).append(pay)
    for month, pays in by_month.items():
        v = etree.SubElement(vers_list, "VersementTraitementSalaire")
        add(v, "mois", int(month.split("-")[1]))
        add(v, "totalVersement", _amount(sum(x["amount"] for x in pays)))
        add(v, "dateDerniereVersment", max(x["payment_date"] for x in pays))   # spelling as in the specification
        details = etree.SubElement(v, "listDetailPaiement")
        for x in pays:
            d = etree.SubElement(details, "DetailPaiementTraitementSalaire")
            add(d, "reference", x.get("reference"))
            add(d, "totalVerse", _amount(x["amount"]))
            add(d, "principal", _amount(x.get("principal") or x["amount"]))
            add(d, "penalite", _amount(x.get("penalty")))
            add(d, "majorations", _amount(x.get("surcharge")))
            add(d, "dateVersement", x["payment_date"])
            add_code(d, "refMoyenPaiement", method_codes.get(x.get("payment_method")))
            add(d, "numQuittance", x.get("receipt_number"))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def find_schema() -> Optional[Path]:
    """Official XSD placed by the user. If several, the one whose name mentions the salary declaration wins."""
    candidates = sorted(Path(settings.edi_schemas_dir).glob("*.xsd"))
    for c in candidates:
        if "salaire" in c.name.lower() or "9421" in c.name:
            return c
    return candidates[0] if candidates else None


def validate_against_schema(xml_bytes: bytes) -> Dict[str, Any]:
    schema_path = find_schema()
    if not schema_path:
        return {"validated": False, "schema": None, "errors": []}
    try:
        schema = etree.XMLSchema(etree.parse(str(schema_path)))
    except (etree.XMLSchemaParseError, etree.XMLSyntaxError) as e:
        return {"validated": False, "schema": schema_path.name, "errors": [f"Schéma illisible : {e}"]}
    doc = etree.fromstring(xml_bytes)
    ok = schema.validate(doc)
    return {"validated": ok, "schema": schema_path.name,
            "errors": [f"Ligne {err.line} : {err.message}" for err in schema.error_log][:50]}


def package(year: int, xml_bytes: bytes, identifiant_fiscal: str) -> str:
    if len(xml_bytes) > MAX_XML_BYTES:
        raise ValueError("Le fichier XML dépasse 15 Mo, limite fixée par la DGI.")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"DTS_9421_{year}_{_digits(identifiant_fiscal) or 'IF'}_{stamp}"
    zip_path = Path(settings.exports_dir) / f"{base}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}.xml", xml_bytes)
    return str(zip_path)
