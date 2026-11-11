"""Catégorisation des lignes de relevé : règles de l'utilisateur, règles apprises de ses corrections, règles de base.

Ordre : règles manuelles (priorité croissante), puis règles apprises (les plus utilisées d'abord), puis règles de base.
Une recette ne reçoit qu'une catégorie de recette, une dépense qu'une catégorie de dépense.
"""
import re
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.core import unified_db
from .templates import normalize

# Règles de base (mots du libellé → code de catégorie préchargée). Volontairement prudentes.
BUILTIN = [
    ("debit", r"\b(frais|commission|agios|tenue de compte|cotisation carte|com )", "FBQ"),
    ("debit", r"\b(salaire|salaires|paie|cnss|cimr|amo)\b", "PERS"),
    ("debit", r"\bloyer\b", "LOC"),
    ("debit", r"\b(station service|carburant|autoroute|oncf|hotel|billet)\b", "DEPL"),
    ("credit", r"\b(subvention|convention|bailleur)\b", "SUBV"),
    ("credit", r"\bdon\b|\bdons\b", "DONS"),
    ("credit", r"\bcotisations?\b", "COTIS"),
    ("credit", r"\b(interets|interet) crediteurs?\b", "PFIN"),
    ("credit", r"\b(prestation|formation)\b", "PREST"),
]
STOP = {"vir", "virement", "recu", "emis", "prlv", "prelevement", "chq", "cheque", "paiement", "tpe", "remise", "sur", "des", "les", "pour", "par"}


@dataclass
class Suggestion:
    category_id: Optional[int] = None
    project_id: Optional[int] = None
    budget_line_id: Optional[int] = None
    source: str = ""          # "règle", "apprise", "base", "liaison"


def learning_pattern(label: str) -> str:
    """Motif appris d'un libellé : ses mots significatifs, sans chiffres (« VIR EMIS PEPINIERE MOYEN ATLAS 12 » → « pepiniere moyen atlas »)."""
    words = [w for w in normalize(label).split() if not any(c.isdigit() for c in w) and len(w) > 2 and w not in STOP]
    return " ".join(words[:3])


class Categorizer:
    def __init__(self, conn: sqlite3.Connection, account_id: int):
        self.conn = conn
        self.account_id = account_id
        self.categories = {r["Id"]: r for r in conn.execute("SELECT Id, Kind, Code, Label FROM Categories WHERE IsActive = 1")}
        self.by_code = {r["Code"]: r["Id"] for r in self.categories.values()}
        self.rules = conn.execute(
            "SELECT * FROM CategorizationRules WHERE IsActive = 1 "
            "ORDER BY CASE Source WHEN 'Manual' THEN 0 ELSE 1 END, Priority, HitCount DESC").fetchall()
        self.lines = conn.execute("SELECT Id, ProjectId, CategoryId FROM BudgetLines WHERE IsDeleted = 0").fetchall()
        self.account = conn.execute("SELECT Purpose FROM BankAccounts WHERE Id = ?", (account_id,)).fetchone()

    def _kind_ok(self, category_id: Optional[int], direction: str) -> bool:
        if category_id is None or category_id not in self.categories:
            return category_id is None
        return self.categories[category_id]["Kind"] == ("Income" if direction == "credit" else "Expense")

    def linked_project(self, date_iso: str) -> tuple[bool, Optional[int]]:
        """(trouvé, projet) d'après les liaisons du compte : projet unique, ou fonctionnement pour un compte de fonctionnement."""
        links = self.conn.execute(
            "SELECT ProjectId FROM AccountProjectLinks WHERE BankAccountId = ? AND IsDeleted = 0 AND ValidFrom <= ? "
            "AND (ValidTo IS NULL OR ValidTo >= ?)", (self.account_id, date_iso, date_iso)).fetchall()
        if len(links) == 1:
            return True, links[0]["ProjectId"]
        if not links and self.account and self.account["Purpose"] == "Operating":
            return True, None
        return False, None

    def suggest(self, label: str, debit: int, credit: int, date_iso: str) -> Suggestion:
        direction = "credit" if credit > 0 else "debit"
        text = normalize(label)
        s = Suggestion()
        for r in self.rules:
            if r["Direction"] and r["Direction"].lower() != direction:
                continue
            pattern = r["Pattern"]
            hit = re.search(pattern, label, re.IGNORECASE) if r["MatchType"] == "Regex" else normalize(pattern) in text
            if hit and self._kind_ok(r["CategoryId"], direction):
                s = Suggestion(r["CategoryId"], r["ProjectId"], r["BudgetLineId"], "apprise" if r["Source"] == "Learned" else "règle")
                break
        if s.category_id is None:
            for d, regex, code in BUILTIN:
                if d == direction and re.search(regex, f" {text} ") and code in self.by_code:
                    s.category_id, s.source = self.by_code[code], "base"
                    break
        if s.project_id is None and s.budget_line_id is None:
            found, project = self.linked_project(date_iso)
            if found:
                s.project_id = project
                s.source = s.source or "liaison"
        if s.budget_line_id is None and s.category_id is not None:
            candidates = [l for l in self.lines if l["ProjectId"] == s.project_id and l["CategoryId"] == s.category_id]
            if len(candidates) == 1:
                s.budget_line_id = candidates[0]["Id"]
        return s


def learn(conn: sqlite3.Connection, label: str, direction: str, category_id: Optional[int],
          project_id: Optional[int], budget_line_id: Optional[int]) -> Optional[int]:
    """Enregistre (ou renforce) une règle apprise d'une correction de l'utilisateur."""
    pattern = learning_pattern(label)
    if not pattern or category_id is None:
        return None
    existing = conn.execute("SELECT * FROM CategorizationRules WHERE Source = 'Learned' AND Pattern = ? AND Direction = ?",
                            (pattern, direction.capitalize())).fetchone()
    if existing:
        unified_db.update(conn, "CategorizationRules", "CategorizationRule", existing["Id"], {
            "CategoryId": category_id, "ProjectId": project_id, "BudgetLineId": budget_line_id, "HitCount": existing["HitCount"] + 1})
        return existing["Id"]
    return unified_db.insert(conn, "CategorizationRules", "CategorizationRule", {
        "Pattern": pattern, "MatchType": "Contains", "Direction": direction.capitalize(), "CategoryId": category_id,
        "ProjectId": project_id, "BudgetLineId": budget_line_id, "Source": "Learned", "Priority": 100, "HitCount": 1, "IsActive": 1})
