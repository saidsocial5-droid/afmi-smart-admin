"""Contrôles de cohérence avant génération d'un rapport annuel. Niveau de chaque contrôle paramétrable
(bloquant, avertissement, ignoré) dans financial_report_layout.json."""
from typing import Any, Dict, List

from . import finance, moral
from .context import Period, Scope


def run(conn, period: Period, scope: Scope, layout: Dict[str, Any]) -> Dict[str, Any]:
    levels = layout.get("checks", {})
    from backend.core import unified_db
    # Seuil commun aux relevés et aux rapports (Paramètres › Comptabilité), sinon celui du fichier de présentation
    threshold = int(round(float(unified_db.get_setting("accounting.receipt_threshold_mad", None) or layout.get("receipt_threshold_mad", 1000)) * 100))
    found: List[Dict[str, Any]] = []

    def add(code: str, message: str, items: List[str]):
        level = levels.get(code, "warning")
        if items and level != "ignore":
            found.append({"code": code, "level": level, "count": len(items), "message": message, "items": items[:15]})

    acc_filter = "" if scope.type == "association" else f" AND o.BankAccountId IN ({','.join(str(a) for a in (scope.account_ids or [-1]))})"
    drafts = conn.execute(f"SELECT o.OperationDate, o.Label, o.AmountMinor FROM Operations o WHERE o.Status = 'Draft' AND o.IsDeleted = 0 "
                          f"AND o.OperationDate BETWEEN ? AND ?{acc_filter} ORDER BY o.OperationDate", (period.start, period.end)).fetchall()
    add("DRAFT_OPERATIONS", "Opérations en brouillon sur l'exercice (non validées, donc absentes des états).",
        [f"{d['OperationDate']} {d['Label']} ({d['AmountMinor'] / 100:.2f})" for d in drafts])

    unpaired = conn.execute(
        "SELECT TransferGroupId FROM Operations WHERE Nature = 'InternalTransfer' AND IsDeleted = 0 AND OperationDate BETWEEN ? AND ? "
        "GROUP BY TransferGroupId HAVING SUM(Direction = 'Debit') <> 1 OR SUM(Direction = 'Credit') <> 1", (period.start, period.end)).fetchall()
    add("UNPAIRED_TRANSFER", "Virements internes incomplets (une seule jambe).", [r[0] for r in unpaired])

    missing_rates = []
    for currency, what in [(r[0], "compte") for r in conn.execute("SELECT DISTINCT Currency FROM BankAccounts WHERE IsDeleted = 0")] + \
                          [(r[0], "ligne budgétaire") for r in conn.execute("SELECT DISTINCT Currency FROM BudgetLines WHERE IsDeleted = 0")]:
        if finance._rate(conn, currency, period.end) is None:
            missing_rates.append(f"{currency} ({what})")
    add("MISSING_RATE", f"Taux de change manquant au {period.end}.", sorted(set(missing_rates)))

    uncategorized = [r for r in finance.allocations(conn, period.start, period.end, scope) if r["CategoryId"] is None]
    add("UNCATEGORIZED", "Écritures validées sans catégorie (classées « — » dans les états).",
        [f"{r['OperationDate']} opération {r['OpId']} ({r['mad'] / 100:.2f} MAD)" for r in uncategorized])

    accounts = conn.execute("SELECT Id, Title FROM BankAccounts WHERE IsDeleted = 0 AND Kind = 'Bank' AND OpeningDate <= ?", (period.end,)).fetchall()
    unrec = []
    for a in accounts:
        if scope.type != "association" and a["Id"] not in (scope.account_ids or []):
            continue
        st = finance.reconciliation_status(conn, a["Id"], period.end)
        if st["status"] != "ok" or (st["statement_end"] or "") < period.end:
            unrec.append(f"{a['Title']} : " + {"none": "aucun relevé", "gap": f"écart {(st['difference'] or 0) / 100:.2f}",
                                                "pending": f"{st['unmatched_lines'] + st['unmatched_ops']} élément(s) non rapproché(s)",
                                                "ok": f"dernier relevé au {st['statement_end']}"}[st["status"]])
    add("UNRECONCILED_ACCOUNT", f"Comptes non rapprochés au {period.end}.", unrec)

    no_receipt = conn.execute(
        f"SELECT o.OperationDate, o.Label, o.AmountMadMinor FROM Operations o WHERE o.Status = 'Validated' AND o.IsDeleted = 0 "
        f"AND o.Nature = 'Expense' AND o.Direction = 'Debit' AND o.AmountMadMinor >= ? AND o.OperationDate BETWEEN ? AND ?{acc_filter} "
        f"AND NOT EXISTS (SELECT 1 FROM OperationAttachments t WHERE t.OperationId = o.Id) ORDER BY o.OperationDate",
        (threshold, period.start, period.end)).fetchall()
    add("MISSING_RECEIPT", f"Dépenses de {threshold // 100} MAD ou plus sans justificatif.",
        [f"{r['OperationDate']} {r['Label']} ({r['AmountMadMinor'] / 100:.2f} MAD)" for r in no_receipt])

    unmeasured = [f"{i['project']} — {i['name']}" for i in moral.indicators(conn, period, scope) if not i["measured"]]
    add("INDICATOR_WITHOUT_MEASURE", "Indicateurs sans mesure datée dans l'exercice (la valeur courante sera utilisée).", unmeasured)

    return {"checks": found, "blocking": any(c["level"] == "blocking" for c in found)}
