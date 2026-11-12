"""Relevés lus (Lot 3) dans la base unique : archivage, brouillon, corrections, contrôles, anomalies, intégration.

Rien n'entre dans les opérations sans validation explicite : un relevé extrait reste un brouillon modifiable ;
« Valider » exige des soldes cohérents ; « Intégrer » crée des opérations en BROUILLON, à ventiler et valider dans
la Trésorerie (règles complètes de Core/Finance). Toutes les écritures sont journalisées (unified_db).
"""
import json
import mimetypes
from decimal import ROUND_HALF_UP, Decimal
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from backend.config.settings import settings
from backend.core import unified_db
from .categorize import Categorizer, learn
from .model import LOW_CONFIDENCE
from .pipeline import PipelineResult

ARCHIVE_DIR = "archives/releves"
FEE_MIN_THRESHOLD = 50_000          # 500 MAD : seuil des frais « inhabituels » sans historique (par défaut)
RECEIPT_THRESHOLD = 100_000         # 1 000 MAD : dépense pour laquelle un justificatif est attendu (par défaut)
MATCH_DAYS = 3


def _setting_minor(key: str, default_minor: int) -> int:
    """Seuil réglé dans Paramètres (en MAD), converti en centimes."""
    value = unified_db.get_setting(key, None)
    return default_minor if value is None else int(round(float(value) * 100))


def fee_threshold() -> int:
    return _setting_minor("bank.fee_alert_min_mad", FEE_MIN_THRESHOLD)


def receipt_threshold() -> int:
    return _setting_minor("accounting.receipt_threshold_mad", RECEIPT_THRESHOLD)


def match_days() -> int:
    """Tolérance de date pour retrouver l'opération d'une ligne (même réglage que le rapprochement)."""
    value = unified_db.get_setting("bank.reconciliation_tolerance_days", None)
    return MATCH_DAYS if value is None else int(value)



class StatementError(ValueError):
    pass


def archive_dir() -> Path:
    d = settings.data_dir / ARCHIVE_DIR
    (d / "pages").mkdir(parents=True, exist_ok=True)
    (d / "meta").mkdir(parents=True, exist_ok=True)
    return d


def _account(conn, account_id: int):
    a = conn.execute("SELECT * FROM BankAccounts WHERE Id = ? AND IsDeleted = 0", (account_id,)).fetchone()
    if a is None:
        raise StatementError("Compte introuvable.")
    return a


def save_extraction(account_id: int, result: PipelineResult, data: bytes, filename: str) -> int:
    """Archive le fichier source et enregistre le relevé extrait en brouillon. Refuse un fichier déjà importé."""
    st = result.statement
    if not st.lines:
        raise StatementError("Aucune opération lue dans ce fichier. " + " ".join(st.warnings[:2]))
    with unified_db.connect() as conn:
        account = _account(conn, account_id)
        existing = conn.execute("SELECT Id FROM StoredFiles WHERE Sha256 = ?", (result.sha256,)).fetchone()
        if existing and conn.execute("SELECT 1 FROM BankStatements WHERE SourceFileId = ? AND IsDeleted = 0", (existing["Id"],)).fetchone():
            raise StatementError(f"« {filename} » a déjà été importé (même fichier).")
        if existing:
            file_id = existing["Id"]
        else:
            ext = Path(filename).suffix.lower() or ".bin"
            rel = f"{ARCHIVE_DIR}/{result.sha256}{ext}"
            (archive_dir() / f"{result.sha256}{ext}").write_bytes(data)
            file_id = unified_db.insert(conn, "StoredFiles", "StoredFile", {
                "Sha256": result.sha256, "RelativePath": rel, "OriginalName": Path(filename).name[:255],
                "MimeType": mimetypes.guess_type(filename)[0] or "application/octet-stream",
                "SizeBytes": len(data), "ImportedAtUtc": unified_db.now_ef()})

        dates = [l.date for l in st.lines if l.date]
        statement_id = unified_db.insert(conn, "BankStatements", "BankStatement", {
            "BankAccountId": account_id,
            "PeriodStart": st.period_start or min(dates), "PeriodEnd": st.period_end or max(dates),
            "OpeningBalanceMinor": st.opening or 0, "ClosingBalanceMinor": st.closing or 0,
            "Source": "Csv" if st.engine == "tableur" else "Ocr", "SourceFileId": file_id, "Template": st.bank_id,
            "Status": "Draft", "ImportedAtUtc": unified_db.now_ef(), "Notes": "", "IsDeleted": 0})

        cat = Categorizer(conn, account_id)
        for l in st.lines:
            s = cat.suggest(l.label, l.debit, l.credit, l.date or st.period_start)
            conf = dict(l.confidence)
            conf.update({"_page": l.page, "_y": l.y, "_source": s.source})
            unified_db.insert(conn, "StatementLines", "StatementLine", {
                "BankStatementId": statement_id, "OperationDate": l.date or st.period_start, "ValueDate": l.value_date,
                "Label": l.label[:500], "Reference": l.reference[:100], "DebitMinor": l.debit, "CreditMinor": l.credit,
                "ConfidenceJson": json.dumps(conf), "SuggestedCategoryId": s.category_id,
                "SuggestedProjectId": s.project_id, "SuggestedBudgetLineId": s.budget_line_id})

    d = archive_dir()
    for i, png in enumerate(result.page_images):
        (d / "pages" / f"{statement_id}_p{i + 1}.png").write_bytes(png)
    meta = {"engine": st.engine, "bank_name": st.bank_name, "rib": st.rib, "pages": len(result.page_images),
            "warnings": st.warnings, "header_confidence": st.confidence, "original_name": Path(filename).name,
            "opening_found": st.opening is not None, "closing_found": st.closing is not None,
            "account_rib": account["Rib"]}
    (d / "meta" / f"{statement_id}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return statement_id


def _meta(statement_id: int) -> Dict[str, Any]:
    f = archive_dir() / "meta" / f"{statement_id}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def page_image(statement_id: int, page: int) -> Path:
    f = archive_dir() / "pages" / f"{statement_id}_p{page}.png"
    if not f.exists():
        raise StatementError("Page introuvable.")
    return f


def list_statements(account_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with unified_db.connect() as conn:
        sql = ("SELECT s.*, a.Title AS AccountTitle, (SELECT COUNT(*) FROM StatementLines l WHERE l.BankStatementId = s.Id) AS LineCount "
               "FROM BankStatements s JOIN BankAccounts a ON a.Id = s.BankAccountId WHERE s.IsDeleted = 0")
        args: tuple = ()
        if account_id:
            sql += " AND s.BankAccountId = ?"
            args = (account_id,)
        rows = conn.execute(sql + " ORDER BY s.PeriodEnd DESC, s.Id DESC", args).fetchall()
    return [{"id": r["Id"], "account_id": r["BankAccountId"], "account": r["AccountTitle"], "period_start": r["PeriodStart"],
             "period_end": r["PeriodEnd"], "opening": r["OpeningBalanceMinor"], "closing": r["ClosingBalanceMinor"],
             "source": r["Source"], "status": r["Status"], "lines": r["LineCount"], "bank": r["Template"]} for r in rows]


def _lines(conn, statement_id: int):
    return conn.execute("SELECT l.*, m.OperationId AS MatchedOperationId FROM StatementLines l "
                        "LEFT JOIN ReconciliationMatches m ON m.StatementLineId = l.Id "
                        "WHERE l.BankStatementId = ? ORDER BY l.OperationDate, l.Id", (statement_id,)).fetchall()


def checks_and_anomalies(conn, st, lines) -> Dict[str, List[Dict[str, Any]]]:
    """Contrôles (bloquants) et anomalies (à examiner) d'un relevé."""
    blocking, anomalies = [], []
    movement = sum(l["CreditMinor"] - l["DebitMinor"] for l in lines)
    if st["OpeningBalanceMinor"] + movement != st["ClosingBalanceMinor"]:
        blocking.append({"code": "BALANCE", "message":
                         f"Solde initial + mouvements = {(st['OpeningBalanceMinor'] + movement) / 100:,.2f} ≠ solde final "
                         f"{st['ClosingBalanceMinor'] / 100:,.2f} : corrigez la ligne mal lue ou les soldes.".replace(",", " ")})
    others = conn.execute("SELECT * FROM BankStatements WHERE BankAccountId = ? AND Id <> ? AND IsDeleted = 0",
                          (st["BankAccountId"], st["Id"])).fetchall()
    if any(o["PeriodStart"] == st["PeriodStart"] and o["PeriodEnd"] == st["PeriodEnd"] and o["ClosingBalanceMinor"] == st["ClosingBalanceMinor"] for o in others):
        blocking.append({"code": "DUPLICATE_STATEMENT", "message": "Ce relevé semble déjà importé (même période et même solde final)."})
    previous = max((o for o in others if o["PeriodEnd"] < st["PeriodStart"]), key=lambda o: o["PeriodEnd"], default=None)
    if previous is not None:
        if previous["ClosingBalanceMinor"] != st["OpeningBalanceMinor"]:
            blocking.append({"code": "CONTINUITY", "message": "Le solde initial ne correspond pas au solde final du relevé précédent."})
        if date.fromisoformat(previous["PeriodEnd"]) + timedelta(days=1) < date.fromisoformat(st["PeriodStart"]):
            anomalies.append({"code": "MISSING_STATEMENT", "message": f"Relevé manquant entre le {previous['PeriodEnd']} et le {st['PeriodStart']}."})

    seen = {}
    for l in lines:
        key = (l["OperationDate"], l["DebitMinor"], l["CreditMinor"], l["Label"].strip().lower())
        if key in seen:
            anomalies.append({"code": "DUPLICATE_LINE", "line_id": l["Id"], "message": f"Ligne en double possible : {l['Label']} du {l['OperationDate']}."})
        seen[key] = l["Id"]

    fee_cat = conn.execute("SELECT Id FROM Categories WHERE Code = 'FBQ'").fetchone()
    if fee_cat:
        history = [r[0] for r in conn.execute(
            "SELECT l.DebitMinor FROM StatementLines l JOIN BankStatements s ON s.Id = l.BankStatementId "
            "WHERE s.BankAccountId = ? AND s.Id <> ? AND s.IsDeleted = 0 AND l.SuggestedCategoryId = ? AND l.DebitMinor > 0",
            (st["BankAccountId"], st["Id"], fee_cat[0]))]
        fee_min = fee_threshold()
        limit = max(fee_min, 3 * median(history)) if len(history) >= 3 else fee_min
        for l in lines:
            if l["SuggestedCategoryId"] == fee_cat[0] and l["DebitMinor"] > limit:
                anomalies.append({"code": "UNUSUAL_FEE", "line_id": l["Id"],
                                  "message": f"Frais bancaires inhabituels : {l['DebitMinor'] / 100:.2f} ({l['Label']})."})

    consumed: Dict[int, int] = {}       # réalisé validé + lignes précédentes de ce relevé, par ligne budgétaire
    flagged = set()
    for l in lines:
        if l["DebitMinor"] > 0 and l["SuggestedBudgetLineId"]:
            bl = conn.execute("SELECT * FROM BudgetLines WHERE Id = ?", (l["SuggestedBudgetLineId"],)).fetchone()
            if bl is not None:
                if bl["Id"] not in consumed:
                    consumed[bl["Id"]] = conn.execute(
                        "SELECT COALESCE(SUM(CASE o.Direction WHEN 'Debit' THEN a.AmountMinor ELSE -a.AmountMinor END), 0) "
                        "FROM OperationAllocations a JOIN Operations o ON o.Id = a.OperationId "
                        "WHERE a.BudgetLineId = ? AND o.Status = 'Validated' AND o.IsDeleted = 0 AND o.Nature = 'Expense'",
                        (bl["Id"],)).fetchone()[0]
                consumed[bl["Id"]] += l["DebitMinor"]
                if consumed[bl["Id"]] > bl["PlannedMinor"] and bl["Id"] not in flagged:
                    flagged.add(bl["Id"])
                    anomalies.append({"code": "OVER_BUDGET", "line_id": l["Id"],
                                      "message": f"Dépassement de la ligne « {bl['Code']} {bl['Label']} » à partir du {l['OperationDate']} : "
                                                 f"{consumed[bl['Id']] / 100:.2f} imputés pour {bl['PlannedMinor'] / 100:.2f} prévus."})
    receipt_min, days = receipt_threshold(), match_days()
    for l in lines:
        if l["DebitMinor"] >= receipt_min:
            op = conn.execute(
                "SELECT o.Id, (SELECT COUNT(*) FROM OperationAttachments t WHERE t.OperationId = o.Id) AS n FROM Operations o "
                "WHERE o.BankAccountId = ? AND o.IsDeleted = 0 AND o.Direction = 'Debit' AND o.AmountMinor = ? "
                "AND o.OperationDate BETWEEN date(?, ?) AND date(?, ?)",
                (st["BankAccountId"], l["DebitMinor"], l["OperationDate"], f"-{days} day", l["OperationDate"], f"+{days} day")).fetchone()
            if op is None or op["n"] == 0:
                anomalies.append({"code": "NO_RECEIPT", "line_id": l["Id"],
                                  "message": f"Dépense de {l['DebitMinor'] / 100:.2f} sans justificatif enregistré ({l['Label']})."})
    low = sum(1 for l in lines for k, v in json.loads(l["ConfidenceJson"]).items() if not k.startswith("_") and isinstance(v, (int, float)) and v < LOW_CONFIDENCE)
    if low:
        anomalies.append({"code": "LOW_CONFIDENCE", "message": f"{low} champ(s) lus avec une confiance faible, surlignés : vérifiez-les sur l'image."})
    return {"blocking": blocking, "anomalies": anomalies}


def get_statement(statement_id: int) -> Dict[str, Any]:
    with unified_db.connect() as conn:
        st = conn.execute("SELECT * FROM BankStatements WHERE Id = ? AND IsDeleted = 0", (statement_id,)).fetchone()
        if st is None:
            raise StatementError("Relevé introuvable.")
        lines = _lines(conn, statement_id)
        result = checks_and_anomalies(conn, st, lines)
        integrated = {r["Reference"] for r in conn.execute("SELECT Reference FROM Operations WHERE Reference LIKE 'REL-%' AND IsDeleted = 0")}
    meta = _meta(statement_id)
    out_lines = []
    for l in lines:
        conf = json.loads(l["ConfidenceJson"])
        out_lines.append({
            "id": l["Id"], "date": l["OperationDate"], "value_date": l["ValueDate"], "label": l["Label"], "reference": l["Reference"],
            "debit": l["DebitMinor"], "credit": l["CreditMinor"],
            "confidence": {k: v for k, v in conf.items() if not k.startswith("_")},
            "page": conf.get("_page", 0), "y": conf.get("_y", 0), "suggestion_source": conf.get("_source", ""),
            "category_id": l["SuggestedCategoryId"], "project_id": l["SuggestedProjectId"], "budget_line_id": l["SuggestedBudgetLineId"],
            "matched_operation_id": l["MatchedOperationId"], "integrated": f"REL-{l['Id']}" in integrated,
        })
    return {"id": st["Id"], "account_id": st["BankAccountId"], "period_start": st["PeriodStart"], "period_end": st["PeriodEnd"],
            "opening": st["OpeningBalanceMinor"], "closing": st["ClosingBalanceMinor"], "status": st["Status"], "source": st["Source"],
            "bank": st["Template"], "meta": meta, "lines": out_lines, **result}


def save_corrections(statement_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Corrections de l'utilisateur (relevé en brouillon). Une catégorie corrigée enrichit les règles apprises."""
    with unified_db.connect() as conn:
        st = conn.execute("SELECT * FROM BankStatements WHERE Id = ? AND IsDeleted = 0", (statement_id,)).fetchone()
        if st is None:
            raise StatementError("Relevé introuvable.")
        if st["Status"] != "Draft":
            raise StatementError("Relevé déjà validé : il n'est plus modifiable.")
        header = {k: payload[src] for src, k in (("period_start", "PeriodStart"), ("period_end", "PeriodEnd"),
                                                   ("opening", "OpeningBalanceMinor"), ("closing", "ClosingBalanceMinor")) if src in payload}
        if header:
            unified_db.update(conn, "BankStatements", "BankStatement", statement_id, header)
        existing = {l["Id"]: l for l in _lines(conn, statement_id)}
        learned = 0
        for item in payload.get("lines", []):
            debit, credit = int(item.get("debit") or 0), int(item.get("credit") or 0)
            if item.get("deleted"):
                if item.get("id") in existing:
                    unified_db.hard_delete(conn, "StatementLines", "StatementLine", item["id"])
                continue
            if debit < 0 or credit < 0 or (debit > 0) == (credit > 0):
                raise StatementError(f"Ligne « {item.get('label', '')} » : un montant au débit OU au crédit, positif.")
            values = {"OperationDate": item["date"], "ValueDate": item.get("value_date") or None, "Label": (item.get("label") or "")[:500],
                      "Reference": (item.get("reference") or "")[:100], "DebitMinor": debit, "CreditMinor": credit,
                      "SuggestedCategoryId": item.get("category_id"), "SuggestedProjectId": item.get("project_id"),
                      "SuggestedBudgetLineId": item.get("budget_line_id")}
            if item.get("id") in existing:
                old = existing[item["id"]]
                conf = json.loads(old["ConfidenceJson"])
                for field, col in (("date", "OperationDate"), ("label", "Label"), ("debit", "DebitMinor"), ("credit", "CreditMinor"), ("value_date", "ValueDate")):
                    if values[col] != old[col]:
                        conf[field] = 100.0       # corrigé par l'utilisateur
                values["ConfidenceJson"] = json.dumps(conf)
                category_changed = (values["SuggestedCategoryId"], values["SuggestedProjectId"], values["SuggestedBudgetLineId"]) != \
                                   (old["SuggestedCategoryId"], old["SuggestedProjectId"], old["SuggestedBudgetLineId"])
                unified_db.update(conn, "StatementLines", "StatementLine", item["id"], values)
                if category_changed and unified_db.get_setting("accounting.auto_learn_rules", True) and learn(conn, values["Label"], "credit" if credit else "debit", values["SuggestedCategoryId"],
                                              values["SuggestedProjectId"], values["SuggestedBudgetLineId"]):
                    learned += 1
            else:
                values.update({"BankStatementId": statement_id, "ConfidenceJson": json.dumps({"date": 100, "label": 100, "debit": 100, "credit": 100, "_source": "saisie"})})
                unified_db.insert(conn, "StatementLines", "StatementLine", values)
    result = get_statement(statement_id)
    result["learned_rules"] = learned
    return result


def validate(statement_id: int) -> Dict[str, Any]:
    """Validation explicite par l'utilisateur : refusée tant qu'un contrôle bloquant n'est pas levé."""
    current = get_statement(statement_id)
    if current["status"] == "Validated":
        return current
    if current["blocking"]:
        raise StatementError(" ".join(b["message"] for b in current["blocking"]))
    with unified_db.connect() as conn:
        unified_db.update(conn, "BankStatements", "BankStatement", statement_id, {"Status": "Validated"})
    return get_statement(statement_id)


def _rate(conn, currency: str, day: str) -> Optional[Decimal]:
    """Taux le plus récent antérieur ou égal à la date (même règle que CurrencyConverter côté Desktop)."""
    if currency == "MAD":
        return None
    r = conn.execute("SELECT RateToMad FROM CurrencyRates WHERE Currency = ? AND Date <= ? ORDER BY Date DESC LIMIT 1", (currency, day)).fetchone()
    if r is None:
        raise StatementError(f"Aucun taux {currency}/MAD connu au {day} : saisissez-le dans Trésorerie → Budget et conventions.")
    return Decimal(str(r[0]))


def integrate(statement_id: int) -> Dict[str, Any]:
    """
    Relevé validé → opérations en BROUILLON (une par ligne non encore comptabilisée), avec l'imputation proposée.
    Une ligne qui correspond déjà à une opération du compte (même montant, ± 3 jours) n'est pas dupliquée : elle sera
    rapprochée dans la Trésorerie. Relancer l'intégration ne crée jamais de doublon.
    """
    created, skipped_existing, already = 0, 0, 0
    with unified_db.connect() as conn:
        st = conn.execute("SELECT * FROM BankStatements WHERE Id = ? AND IsDeleted = 0", (statement_id,)).fetchone()
        if st is None:
            raise StatementError("Relevé introuvable.")
        if st["Status"] != "Validated":
            raise StatementError("Validez d'abord le relevé (contrôle des lignes et des soldes).")
        account = _account(conn, st["BankAccountId"])
        if account["Status"] != "Active":
            raise StatementError("Compte clôturé : intégration impossible.")
        categories = {r["Id"]: r["Kind"] for r in conn.execute("SELECT Id, Kind FROM Categories")}
        days = match_days()
        for l in _lines(conn, statement_id):
            ref = f"REL-{l['Id']}"
            if conn.execute("SELECT 1 FROM Operations WHERE Reference = ? AND IsDeleted = 0", (ref,)).fetchone():
                already += 1
                continue
            is_credit = l["CreditMinor"] > 0
            amount = l["CreditMinor"] or l["DebitMinor"]
            duplicate = conn.execute(
                "SELECT 1 FROM Operations o WHERE o.BankAccountId = ? AND o.IsDeleted = 0 AND o.AmountMinor = ? AND o.Direction = ? "
                "AND o.OperationDate BETWEEN date(?, ?) AND date(?, ?) "
                "AND NOT EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.OperationId = o.Id)",
                (account["Id"], amount, "Credit" if is_credit else "Debit", l["OperationDate"], f"-{days} day",
                 l["OperationDate"], f"+{days} day")).fetchone()
            if duplicate:
                skipped_existing += 1
                continue
            if l["OperationDate"] < account["OpeningDate"]:
                raise StatementError(f"Ligne du {l['OperationDate']} antérieure à l'ouverture du compte.")
            kind = categories.get(l["SuggestedCategoryId"])
            nature = "Income" if (kind == "Income" or (kind is None and is_credit)) else "Expense"
            rate = _rate(conn, account["Currency"], l["OperationDate"])
            mad = amount if rate is None else int((Decimal(amount) * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            op_id = unified_db.insert(conn, "Operations", "Operation", {
                "BankAccountId": account["Id"], "OperationDate": l["OperationDate"], "ValueDate": l["ValueDate"],
                "Label": l["Label"], "Reference": ref, "ThirdParty": "", "Direction": "Credit" if is_credit else "Debit",
                "Nature": nature, "AmountMinor": amount, "Currency": account["Currency"], "RateToMad": None if rate is None else str(rate),
                "AmountMadMinor": mad, "TransferGroupId": None, "Status": "Draft", "ValidatedAtUtc": None, "ValidatedBy": "",
                "Notes": f"Importé du relevé n° {statement_id} (ligne {l['Id']}) : à vérifier, ventiler et valider.", "IsDeleted": 0})
            if l["SuggestedBudgetLineId"]:
                unified_db.insert(conn, "OperationAllocations", "OperationAllocation", {
                    "OperationId": op_id, "ProjectId": l["SuggestedProjectId"], "BudgetLineId": l["SuggestedBudgetLineId"],
                    "CategoryId": l["SuggestedCategoryId"], "AmountMinor": amount})
            created += 1
    return {"created": created, "skipped_existing": skipped_existing, "already_integrated": already}


def delete(statement_id: int) -> None:
    with unified_db.connect() as conn:
        st = conn.execute("SELECT * FROM BankStatements WHERE Id = ? AND IsDeleted = 0", (statement_id,)).fetchone()
        if st is None:
            raise StatementError("Relevé introuvable.")
        if conn.execute("SELECT 1 FROM ReconciliationMatches m JOIN StatementLines l ON l.Id = m.StatementLineId WHERE l.BankStatementId = ?",
                        (statement_id,)).fetchone():
            raise StatementError("Des lignes de ce relevé sont rapprochées : annulez d'abord les rapprochements.")
        unified_db.soft_delete(conn, "BankStatements", "BankStatement", statement_id)


def context() -> Dict[str, Any]:
    """Listes pour l'écran : comptes actifs, catégories, projets, lignes budgétaires."""
    with unified_db.connect() as conn:
        return {
            "accounts": [dict(id=r["Id"], title=r["Title"], currency=r["Currency"], bank=r["BankName"])
                         for r in conn.execute("SELECT * FROM BankAccounts WHERE IsDeleted = 0 AND Status = 'Active' ORDER BY Title")],
            "categories": [dict(id=r["Id"], kind=r["Kind"], label=r["Label"])
                           for r in conn.execute("SELECT * FROM Categories WHERE IsActive = 1 ORDER BY Kind, Label")],
            "projects": [dict(id=r["Id"], code=r["Code"], name=r["Name"])
                         for r in conn.execute("SELECT Id, Code, Name FROM Projects WHERE IsDeleted = 0 ORDER BY Code")],
            "budget_lines": [dict(id=r["Id"], project_id=r["ProjectId"], code=r["Code"], label=r["Label"])
                             for r in conn.execute("SELECT * FROM BudgetLines WHERE IsDeleted = 0 ORDER BY Code")],
        }
