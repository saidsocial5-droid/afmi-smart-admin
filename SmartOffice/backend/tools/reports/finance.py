"""États financiers du rapport annuel, calculés depuis la base unique.

Une opération validée est répartie sur ses ventilations ; sa contre-valeur MAD est répartie au plus fort reste,
comme AllocationSplitter côté .NET : la somme des parts est exactement la contre-valeur de l'opération.
Recettes nettes des restitutions, dépenses nettes des avoirs, virements internes exclus (comme FinanceService).
"""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from .context import Period, Scope
from .i18n import t


def split_minor(total: int, weights: List[int]) -> List[int]:
    """Répartition au plus fort reste (identique à AllocationSplitter, vecteurs partagés)."""
    s = sum(weights)
    if s == 0:
        return [0] * len(weights)
    exact = [Decimal(total) * Decimal(w) / Decimal(s) for w in weights]
    parts = [int(e.to_integral_value(rounding="ROUND_FLOOR")) for e in exact]
    remainder = total - sum(parts)
    for i in sorted(range(len(parts)), key=lambda i: (-(exact[i] - parts[i]), i))[:remainder]:
        parts[i] += 1
    return parts


def allocations(conn, start: str, end: str, scope: Scope) -> List[Dict[str, Any]]:
    """Ventilations des opérations validées de la période, avec leur part MAD signée (recette + / dépense +)."""
    rows = conn.execute(
        "SELECT a.Id AS AllocId, a.ProjectId, a.BudgetLineId, a.CategoryId, a.AmountMinor AS AllocAmount, o.Id AS OpId, o.Direction, "
        "o.Nature, o.AmountMinor AS OpAmount, o.AmountMadMinor, o.OperationDate, o.BankAccountId, c.Code AS CatCode, c.Label AS CatLabel, "
        "p.Code AS ProjCode, p.Name AS ProjName, p.FunderId AS ProjFunder, "
        "(SELECT ag.FunderId FROM FundingTranches t JOIN FundingAgreements ag ON ag.Id = t.FundingAgreementId "
        "  WHERE t.ReceivedOperationId = o.Id AND t.IsDeleted = 0 LIMIT 1) AS TrancheFunder "
        "FROM OperationAllocations a JOIN Operations o ON o.Id = a.OperationId "
        "LEFT JOIN Categories c ON c.Id = a.CategoryId LEFT JOIN Projects p ON p.Id = a.ProjectId "
        "WHERE o.Status = 'Validated' AND o.IsDeleted = 0 AND o.Nature IN ('Income', 'Expense') "
        "AND o.OperationDate >= ? AND o.OperationDate <= ? ORDER BY o.Id, a.Id", (start, end)).fetchall()
    by_op: Dict[int, List] = defaultdict(list)
    for r in rows:
        by_op[r["OpId"]].append(r)
    out = []
    for op_rows in by_op.values():
        first = op_rows[0]
        shares = split_minor(first["AmountMadMinor"], [r["AllocAmount"] for r in op_rows])
        positive = (first["Nature"] == "Income") == (first["Direction"] == "Credit")
        for r, share in zip(op_rows, shares):
            if scope.project_ids is not None and r["ProjectId"] not in scope.project_ids:
                continue
            out.append({**dict(r), "mad": share if positive else -share,
                        "funder_id": r["TrancheFunder"] or r["ProjFunder"]})
    return out


def totals(conn, period: Period, scope: Scope) -> Dict[str, int]:
    rows = allocations(conn, period.start, period.end, scope)
    income = sum(r["mad"] for r in rows if r["Nature"] == "Income")
    expense = sum(r["mad"] for r in rows if r["Nature"] == "Expense")
    return {"income": income, "expense": expense, "result": income - expense}


def _table(title: str, columns: List[str], rows: List[List[Any]], total: Optional[List[Any]] = None,
           notes: Optional[List[str]] = None, source: str = "", chart: Optional[Dict[str, Any]] = None,
           formats: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tableau générique ; formats par colonne : text, money (centimes), number, percent."""
    return {"title": title, "columns": columns, "rows": rows, "total": total, "notes": notes or [], "source": source, "chart": chart,
            "formats": formats or (["text"] + ["money"] * (len(columns) - 1))}


def _names(conn) -> Dict[str, Dict[int, str]]:
    return {"funders": {r["Id"]: r["Name"] for r in conn.execute("SELECT Id, Name FROM Funders")}}


def cer(conn, period: Period, scope: Scope, layout: Dict[str, Any], lang: str = "fr") -> Dict[str, Any]:
    """Compte d'emploi des ressources selon la présentation paramétrée (config/financial_report_layout.json)."""
    rows_all = allocations(conn, period.start, period.end, scope)
    funders = _names(conn)["funders"]
    other_label = t(lang, "operating")
    rows: List[List[Any]] = []
    uses_total = 0
    rows.append([f"**{t(lang, 'uses')}**", None])
    for section in layout["cer"]["uses"]:
        if section["source"] == "operating" and not scope.include_operating:
            continue
        sel = [r for r in rows_all if r["Nature"] == "Expense" and ((r["ProjectId"] is None) == (section["source"] == "operating"))]
        amount = sum(r["mad"] for r in sel)
        uses_total += amount
        rows.append([section["label"], amount])
        detail = defaultdict(int)
        for r in sel:
            key = (f"{r['ProjCode']} — {r['ProjName']}" if section.get("detail") == "project" else (r["CatLabel"] or other_label))
            detail[key] += r["mad"]
        rows += [[f"    {k}", v] for k, v in sorted(detail.items())]
    rows.append([f"**{t(lang, 'total')} {t(lang, 'uses').lower()}**", uses_total])

    res_total = 0
    rows.append([f"**{t(lang, 'resources')}**", None])
    income = [r for r in rows_all if r["Nature"] == "Income"]
    claimed = set()
    for section in layout["cer"]["resources"]:
        cats = section["categories"]
        sel = [r for r in income if r["AllocId"] not in claimed and ("*" in cats or r["CatCode"] in cats)]
        claimed |= {r["AllocId"] for r in sel}
        amount = sum(r["mad"] for r in sel)
        if amount == 0 and "*" in cats:
            continue
        res_total += amount
        rows.append([section["label"], amount])
        if section.get("detail") == "funder":
            detail = defaultdict(int)
            for r in sel:
                detail[funders.get(r["funder_id"], "—")] += r["mad"]
            rows += [[f"    {k}", v] for k, v in sorted(detail.items())]
    rows.append([f"**{t(lang, 'total')} {t(lang, 'resources').lower()}**", res_total])
    return _table(t(lang, "cer"), [t(lang, "nature"), "MAD"], rows, [t(lang, "result"), res_total - uses_total],
                  [layout.get("status_note", t(lang, "provisional"))], "Opérations validées (Trésorerie)", formats=["text", "money"])


def income_expense(conn, period: Period, scope: Scope, lang: str = "fr") -> Dict[str, Any]:
    """Matrice nature × projet (colonne fonctionnement comprise), recettes puis dépenses."""
    rows_all = allocations(conn, period.start, period.end, scope)
    cols = sorted({r["ProjCode"] or t(lang, "operating") for r in rows_all}, key=lambda c: (c == t(lang, "operating"), c))
    matrix: Dict[tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows_all:
        matrix[(r["Nature"], r["CatLabel"] or "—")][r["ProjCode"] or t(lang, "operating")] += r["mad"]
    rows = []
    totals_col = defaultdict(int)
    for nature, header in (("Income", t(lang, "resources")), ("Expense", t(lang, "uses"))):
        keys = sorted(k for k in matrix if k[0] == nature)
        if not keys:
            continue
        rows.append([f"**{header}**"] + [None] * (len(cols) + 1))
        for k in keys:
            vals = [matrix[k].get(c, 0) for c in cols]
            rows.append([k[1]] + vals + [sum(vals)])
        sub = [sum(matrix[k].get(c, 0) for k in keys) for c in cols]
        rows.append([f"**{t(lang, 'total')} {header.lower()}**"] + sub + [sum(sub)])
        for c, v in zip(cols, sub):
            totals_col[c] += v if nature == "Income" else -v
    result = [totals_col.get(c, 0) for c in cols]
    return _table(t(lang, "income_expense"), [t(lang, "nature")] + cols + [t(lang, "total")], rows,
                  [t(lang, "result")] + result + [sum(result)], [], "Opérations validées (Trésorerie)")


def _rate(conn, currency: str, day: str) -> Optional[Decimal]:
    if currency == "MAD":
        return Decimal(1)
    r = conn.execute("SELECT RateToMad FROM CurrencyRates WHERE Currency = ? AND Date <= ? ORDER BY Date DESC LIMIT 1", (currency, day)).fetchone()
    return Decimal(str(r[0])) if r else None


def budget_execution(conn, period: Period, scope: Scope, by: str = "project", lang: str = "fr") -> Dict[str, Any]:
    """
    Prévu / réalisé / écart / taux. Lignes rattachées à l'exercice : réalisé de l'exercice ; lignes pluriannuelles
    (sans exercice) : réalisé cumulé jusqu'à la fin de l'exercice.
    """
    fy = conn.execute("SELECT Id FROM FiscalYears WHERE Year = ?", (period.year,)).fetchone()
    lines = conn.execute(
        "SELECT l.*, p.Code AS ProjCode, p.Name AS ProjName, p.FunderId AS ProjFunder, ag.FunderId AS AgFunder "
        "FROM BudgetLines l LEFT JOIN Projects p ON p.Id = l.ProjectId LEFT JOIN FundingAgreements ag ON ag.Id = l.FundingAgreementId "
        "WHERE l.IsDeleted = 0 AND (l.FiscalYearId IS NULL OR l.FiscalYearId = ?)", (fy[0] if fy else -1,)).fetchall()
    year_allocs = {}
    for r in allocations(conn, period.start, period.end, Scope("association", None, "")):
        if r["Nature"] == "Expense" and r["BudgetLineId"]:
            year_allocs[r["BudgetLineId"]] = year_allocs.get(r["BudgetLineId"], 0) + r["mad"]
    cumul = {}
    for r in allocations(conn, "0001-01-01", period.end, Scope("association", None, "")):
        if r["Nature"] == "Expense" and r["BudgetLineId"]:
            cumul[r["BudgetLineId"]] = cumul.get(r["BudgetLineId"], 0) + r["mad"]
    funders = _names(conn)["funders"]
    groups: Dict[str, List] = defaultdict(list)
    notes = []
    for l in lines:
        if scope.project_ids is not None and l["ProjectId"] not in scope.project_ids:
            continue
        if scope.project_ids is None and l["ProjectId"] is None and not scope.include_operating:
            continue
        rate = _rate(conn, l["Currency"], period.end)
        if rate is None:
            notes.append(f"Ligne {l['Code']} {l['Label']} ignorée : aucun taux {l['Currency']}/MAD.")
            continue
        planned = int((Decimal(l["PlannedMinor"]) * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        realized = year_allocs.get(l["Id"], 0) if l["FiscalYearId"] else cumul.get(l["Id"], 0)
        if by == "funder":
            key = funders.get(l["AgFunder"] or l["ProjFunder"], t(lang, "operating") if l["ProjectId"] is None else "—")
        else:
            key = f"{l['ProjCode']} — {l['ProjName']}" if l["ProjectId"] else t(lang, "operating")
        groups[key].append([f"{l['Code']} {l['Label']}".strip(), planned, realized])
    rows = []
    tp = tr = 0
    for key in sorted(groups):
        gp = sum(x[1] for x in groups[key])
        gr = sum(x[2] for x in groups[key])
        rows.append([f"**{key}**", gp, gr, gp - gr, _pct(gr, gp)])
        rows += [[f"    {n}", p, r, p - r, _pct(r, p)] for n, p, r in groups[key]]
        tp, tr = tp + gp, tr + gr
    title = f"{t(lang, 'budget_exec')} {t(lang, 'by_funder' if by == 'funder' else 'by_project')}"
    notes.append("Lignes de l'exercice : réalisé de l'exercice ; lignes pluriannuelles : réalisé cumulé à la fin de l'exercice.")
    return _table(title, [t(lang, "line"), t(lang, "planned"), t(lang, "realized"), t(lang, "gap"), t(lang, "rate")], rows,
                  [t(lang, "total"), tp, tr, tp - tr, _pct(tr, tp)], notes, "Lignes budgétaires et opérations validées",
                  formats=["text", "money", "money", "money", "percent"])


def _pct(part: int, whole: int) -> Optional[float]:
    return round(100 * part / whole, 1) if whole else None


def reconciliation_status(conn, account_id: int, end: str) -> Dict[str, Any]:
    """État du dernier relevé de la période (même formule que ReconciliationService.GetReport côté .NET)."""
    st = conn.execute("SELECT * FROM BankStatements WHERE BankAccountId = ? AND IsDeleted = 0 AND PeriodEnd <= ? "
                      "ORDER BY PeriodEnd DESC LIMIT 1", (account_id, end)).fetchone()
    if st is None:
        return {"status": "none", "difference": None, "unmatched_lines": 0, "unmatched_ops": 0, "statement_end": None}
    first = conn.execute("SELECT MIN(PeriodStart) FROM BankStatements WHERE BankAccountId = ? AND IsDeleted = 0 AND PeriodEnd <= ?",
                         (account_id, st["PeriodEnd"])).fetchone()[0]
    lines = conn.execute(
        "SELECT l.CreditMinor - l.DebitMinor AS s FROM StatementLines l JOIN BankStatements b ON b.Id = l.BankStatementId "
        "WHERE b.BankAccountId = ? AND b.IsDeleted = 0 AND b.PeriodEnd <= ? "
        "AND NOT EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.StatementLineId = l.Id)", (account_id, st["PeriodEnd"])).fetchall()
    ops = conn.execute(
        "SELECT CASE Direction WHEN 'Credit' THEN AmountMinor ELSE -AmountMinor END AS s FROM Operations o "
        "WHERE o.BankAccountId = ? AND o.Status = 'Validated' AND o.IsDeleted = 0 AND o.OperationDate >= ? AND o.OperationDate <= ? "
        "AND NOT EXISTS (SELECT 1 FROM ReconciliationMatches m WHERE m.OperationId = o.Id)", (account_id, first, st["PeriodEnd"])).fetchall()
    book = book_balance(conn, account_id, st["PeriodEnd"])
    adjusted = st["ClosingBalanceMinor"] + sum(r["s"] for r in ops) - sum(r["s"] for r in lines)
    diff = book - adjusted
    status = "ok" if diff == 0 and not lines and not ops else ("gap" if diff else "pending")
    return {"status": status, "difference": diff, "unmatched_lines": len(lines), "unmatched_ops": len(ops), "statement_end": st["PeriodEnd"]}


def book_balance(conn, account_id: int, day: str) -> int:
    a = conn.execute("SELECT OpeningBalanceMinor, OpeningDate FROM BankAccounts WHERE Id = ?", (account_id,)).fetchone()
    if a is None or day < a["OpeningDate"]:
        return 0
    mv = conn.execute("SELECT COALESCE(SUM(CASE Direction WHEN 'Credit' THEN AmountMinor ELSE -AmountMinor END), 0) FROM Operations "
                      "WHERE BankAccountId = ? AND Status = 'Validated' AND IsDeleted = 0 AND OperationDate <= ?", (account_id, day)).fetchone()[0]
    return a["OpeningBalanceMinor"] + mv


def treasury(conn, period: Period, scope: Scope, lang: str = "fr") -> Dict[str, Any]:
    accounts = conn.execute("SELECT * FROM BankAccounts WHERE IsDeleted = 0 AND OpeningDate <= ? ORDER BY Title", (period.end,)).fetchall()
    if scope.account_ids is not None and scope.type != "association":
        accounts = [a for a in accounts if a["Id"] in scope.account_ids]
    labels = {"ok": "✔ rapproché", "gap": "écart {d}", "pending": "{n} élément(s) non rapproché(s)", "none": "aucun relevé"}
    rows, total, notes = [], 0, []
    for a in accounts:
        bal = book_balance(conn, a["Id"], period.end)
        rate = _rate(conn, a["Currency"], period.end)
        mad = None if rate is None else int((Decimal(bal) * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if mad is None:
            notes.append(f"{a['Title']} : aucun taux {a['Currency']}/MAD au {period.end}.")
        rec = reconciliation_status(conn, a["Id"], period.end)
        text = labels[rec["status"]].format(d=f"{(rec['difference'] or 0) / 100:,.2f}".replace(",", " "),
                                            n=rec["unmatched_lines"] + rec["unmatched_ops"])
        if rec["statement_end"] and rec["statement_end"] < period.end:
            text += f" (relevé au {rec['statement_end']})"
        rows.append([a["Title"], a["Currency"], bal, mad, text])
        total += mad or 0
    return _table(t(lang, "treasury", end=period.end), [t(lang, "account"), "Devise", t(lang, "balance"), "MAD", t(lang, "reconciliation")],
                  rows, [t(lang, "total"), None, None, total, None], notes, "Comptes, opérations validées, relevés et rapprochements",
                  formats=["text", "text", "money", "money", "text"])


def carry_forward(conn, period: Period, scope: Scope, lang: str = "fr") -> Dict[str, Any]:
    """Par convention : reçu et utilisé (exercice et cumul), solde non utilisé reporté. Traitement comptable à valider."""
    agreements = conn.execute("SELECT ag.*, f.Name AS FunderName, p.Code AS ProjCode FROM FundingAgreements ag "
                              "JOIN Funders f ON f.Id = ag.FunderId JOIN Projects p ON p.Id = ag.ProjectId WHERE ag.IsDeleted = 0").fetchall()
    every = Scope("association", None, "")
    cum = allocations(conn, "0001-01-01", period.end, every)
    yr = allocations(conn, period.start, period.end, every)
    line_agreement = {r["Id"]: r["FundingAgreementId"] for r in conn.execute("SELECT Id, FundingAgreementId FROM BudgetLines")}
    tranche_ops = defaultdict(set)
    for r in conn.execute("SELECT FundingAgreementId, ReceivedOperationId FROM FundingTranches WHERE ReceivedOperationId IS NOT NULL AND IsDeleted = 0"):
        tranche_ops[r[0]].add(r[1])

    def belongs(r, ag_id):
        return line_agreement.get(r["BudgetLineId"]) == ag_id or (r["Nature"] == "Income" and r["OpId"] in tranche_ops[ag_id])

    rows = []
    for ag in agreements:
        if scope.project_ids is not None and ag["ProjectId"] not in scope.project_ids:
            continue
        rec_y = sum(r["mad"] for r in yr if r["Nature"] == "Income" and belongs(r, ag["Id"]))
        spent_y = sum(r["mad"] for r in yr if r["Nature"] == "Expense" and belongs(r, ag["Id"]))
        rec_c = sum(r["mad"] for r in cum if r["Nature"] == "Income" and belongs(r, ag["Id"]))
        spent_c = sum(r["mad"] for r in cum if r["Nature"] == "Expense" and belongs(r, ag["Id"]))
        rows.append([f"{ag['Reference']} — {ag['FunderName']} ({ag['ProjCode']})", rec_y, spent_y, rec_c, spent_c, rec_c - spent_c])
    total = [t(lang, "total")] + [sum(r[i] for r in rows) for i in range(1, 6)]
    return _table(t(lang, "carry"), [t(lang, "agreement"), f"{t(lang, 'received')} {period.year}", f"{t(lang, 'spent')} {period.year}",
                                     f"{t(lang, 'received')} (cumul)", f"{t(lang, 'spent')} (cumul)", t(lang, "remaining")],
                  rows, total, ["Montants en MAD, rattachés à une convention par ses lignes budgétaires et ses tranches encaissées.",
                                "Le traitement comptable des fonds non utilisés (fonds dédiés, produits constatés d'avance…) est à valider avec l'expert-comptable."],
                  "Conventions, tranches et opérations validées")


def comparison(conn, period: Period, scope: Scope, layout: Dict[str, Any], lang: str = "fr") -> Dict[str, Any]:
    prev = period.previous()
    cur_rows = {r[0]: r[1] for r in cer(conn, period, scope, layout, lang)["rows"] if not r[0].startswith("    ") and r[1] is not None}
    prev_rows = {r[0]: r[1] for r in cer(conn, prev, scope, layout, lang)["rows"] if not r[0].startswith("    ") and r[1] is not None}
    keys = list(dict.fromkeys([*cur_rows, *prev_rows]))
    rows = []
    for k in keys:
        n, p = cur_rows.get(k, 0), prev_rows.get(k, 0)
        if n == 0 and p == 0:
            continue
        rows.append([k, p, n, n - p, _pct(n - p, p) if p else None])
    tn, tp_ = totals(conn, period, scope), totals(conn, prev, scope)
    chart = {"type": "bars", "series": [{"label": t(lang, "resources"), "planned": tp_["income"] / 100, "actual": tn["income"] / 100},
                                        {"label": t(lang, "uses"), "planned": tp_["expense"] / 100, "actual": tn["expense"] / 100}],
             "legend": [str(prev.year), str(period.year)]}
    return _table(t(lang, "comparison", prev=prev.year), [t(lang, "nature"), str(prev.year), str(period.year), t(lang, "variation"), "%"],
                  rows, [t(lang, "result"), tp_["result"], tn["result"], tn["result"] - tp_["result"], None], [], "Opérations validées", chart,
                  formats=["text", "money", "money", "money", "percent"])


def charts(conn, period: Period, scope: Scope, layout: Dict[str, Any], lang: str = "fr") -> Dict[str, Any]:
    """Répartition des ressources (par section du CER) et des emplois (par nature)."""
    rows = allocations(conn, period.start, period.end, scope)
    res = defaultdict(int)
    claimed = set()
    income = [r for r in rows if r["Nature"] == "Income"]
    for section in layout["cer"]["resources"]:
        sel = [r for r in income if r["AllocId"] not in claimed and ("*" in section["categories"] or r["CatCode"] in section["categories"])]
        claimed |= {r["AllocId"] for r in sel}
        if sel:
            res[section["label"]] += sum(r["mad"] for r in sel)
    uses = defaultdict(int)
    for r in rows:
        if r["Nature"] == "Expense":
            uses[r["CatLabel"] or "—"] += r["mad"]
    return {"title": t(lang, "charts"), "pies": [
        {"title": t(lang, "resources"), "slices": [{"label": k, "value": v / 100} for k, v in res.items() if v > 0]},
        {"title": t(lang, "uses"), "slices": [{"label": k, "value": v / 100} for k, v in uses.items() if v > 0]},
    ], "source": "Opérations validées"}
