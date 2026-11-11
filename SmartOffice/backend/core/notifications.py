"""Alertes envoyées par e-mail (Lot 8) : échéances des bailleurs, trésorerie, rapprochement, sauvegardes.

Vérifiées au démarrage du module Smart Office puis toutes les heures. Un message récapitulatif n'est envoyé que s'il
contient au moins une alerte nouvelle (une alerte déjà signalée n'est rappelée qu'après 7 jours), à destination des
adresses de Paramètres › Notifications. Rien n'est envoyé depuis la base de démonstration ni sans SMTP configuré.
"""
import asyncio
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.core import smtp, unified_db

STATE_KEY = "notifications.state"
REMIND_DAYS = 7


def collect() -> List[Dict[str, Any]]:
    """Alertes en cours, selon les catégories choisies dans les paramètres."""
    from backend.tools.ged import lifecycle
    from backend.tools.reports import finance
    events = unified_db.get_setting("notifications.events", None) or {"obligations": True, "treasury": True, "reconciliation": False, "backup_failure": True}
    out: List[Dict[str, Any]] = []
    if events.get("obligations"):
        for a in lifecycle.alerts():
            if a["code"] in ("REPORT_LATE", "REPORT_DUE", "AGREEMENT_ENDING"):
                out.append({"kind": "Échéances", "message": a["message"]})
    today = date.today().isoformat()
    with unified_db.connect() as conn:
        accounts = conn.execute("SELECT * FROM BankAccounts WHERE IsDeleted = 0 AND Status = 'Active'").fetchall()
        for a in accounts:
            if events.get("treasury"):
                bal = finance.book_balance(conn, a["Id"], today)
                if bal < 0:
                    out.append({"kind": "Trésorerie", "message": f"{a['Title']} : solde négatif ({bal / 100:,.2f} {a['Currency']})".replace(",", " ")})
                elif a["LowBalanceThresholdMinor"] is not None and bal < a["LowBalanceThresholdMinor"]:
                    out.append({"kind": "Trésorerie", "message": f"{a['Title']} : solde de {bal / 100:,.2f} {a['Currency']} sous le seuil d'alerte "
                                                                 f"({a['LowBalanceThresholdMinor'] / 100:,.2f})".replace(",", " ")})
            if events.get("reconciliation"):
                rec = finance.reconciliation_status(conn, a["Id"], today)
                if rec["status"] in ("gap", "pending"):
                    out.append({"kind": "Rapprochement", "message": f"{a['Title']} : {rec['unmatched_lines'] + rec['unmatched_ops']} élément(s) non rapproché(s) "
                                                                    f"au relevé du {rec['statement_end']}."})
    if events.get("backup_failure"):
        err = unified_db.get_setting("backup.last_error", "")
        if err:
            out.append({"kind": "Sauvegardes", "message": f"La dernière sauvegarde automatique a échoué : {err}"})
    for a in out:
        a["key"] = hashlib.sha1(f"{a['kind']}|{a['message']}".encode()).hexdigest()[:16]
    return out


def _recipients() -> List[str]:
    raw = unified_db.get_setting("notifications.recipients", "") or ""
    if not raw:
        with unified_db.connect() as conn:
            r = conn.execute("SELECT RecipientEmail FROM SmtpSettings ORDER BY Id LIMIT 1").fetchone()
        raw = r["RecipientEmail"] if r else ""
    return [x.strip() for x in raw.replace(";", ",").split(",") if "@" in x]


def run(force: bool = False, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Envoie le récapitulatif s'il y a du nouveau (ou tout, avec force). Retourne ce qui a été fait."""
    if os.getenv("AFMI_DEMO") == "1":
        return {"sent": False, "reason": "Base de démonstration : aucun envoi."}
    if not unified_db.is_available():
        return {"sent": False, "reason": "Base indisponible."}
    alerts = collect()
    now = now or datetime.now()
    state = unified_db.get_setting(STATE_KEY, None) or {"sent": {}}
    fresh = [a for a in alerts if force or a["key"] not in state["sent"]
             or datetime.fromisoformat(state["sent"][a["key"]]) < now - timedelta(days=REMIND_DAYS)]
    if not fresh:
        return {"sent": False, "reason": "Aucune alerte nouvelle.", "alerts": len(alerts)}
    recipients = _recipients()
    if not recipients:
        return {"sent": False, "reason": "Aucun destinataire (Paramètres › Notifications).", "alerts": len(alerts)}
    assoc = unified_db.get_setting("association.name", "AFMI") or "AFMI"
    lines = [f"Alertes d'AFMI Smart Admin pour {assoc} — {now:%d/%m/%Y %H:%M}", ""]
    for kind in dict.fromkeys(a["kind"] for a in alerts):
        lines.append(kind)
        lines += [f"  {'[nouveau] ' if a in fresh else ''}{a['message']}" for a in alerts if a["kind"] == kind]
        lines.append("")
    lines.append("Message automatique : les préférences se règlent dans Paramètres › Notifications.")
    try:
        smtp.send(f"[{assoc}] {len(fresh)} alerte(s) nouvelle(s)", "\n".join(lines), recipients)
    except smtp.SmtpError as e:
        return {"sent": False, "reason": str(e), "alerts": len(alerts)}
    for a in alerts:
        if a in fresh:
            state["sent"][a["key"]] = now.isoformat(timespec="seconds")
    current = {a["key"] for a in alerts}
    state["sent"] = {k: v for k, v in state["sent"].items() if k in current}      # alertes levées : oubliées
    unified_db.set_setting(STATE_KEY, state)
    with unified_db.connect() as conn:
        unified_db.append_audit(conn, "Notification", "alertes", "Envoi", {"recipients": len(recipients), "alerts": len(fresh)})
    return {"sent": True, "recipients": recipients, "alerts": len(alerts), "new": len(fresh)}


async def scheduler(interval_seconds: int = 3600) -> None:
    """Boucle de fond du backend (désactivée pendant les tests : AFMI_DISABLE_SCHEDULER=1)."""
    await asyncio.sleep(60)
    while True:
        try:
            await asyncio.to_thread(run)
        except Exception as e:  # noqa: BLE001 — une alerte ne doit jamais arrêter le backend
            print(f"[Notifications] {e}")
        await asyncio.sleep(interval_seconds)
