"""Messagerie (Lot 7) : réglages SMTP partagés avec l'application de bureau (table SmtpSettings, mot de passe chiffré
par DPAPI comme SecretProtector) et envoi d'un e-mail de test depuis les paramètres."""
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict

from backend.core import dpapi, unified_db


class SmtpError(ValueError):
    pass


def get() -> Dict[str, Any]:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM SmtpSettings ORDER BY Id LIMIT 1").fetchone()
    if r is None:
        return {"server": "", "port": 587, "username": "", "recipient": "", "schedule": "Aucun", "password_configured": False}
    return {"server": r["Server"], "port": r["Port"], "username": r["Username"], "recipient": r["RecipientEmail"],
            "schedule": r["ScheduleType"], "password_configured": bool(r["Password"]), "last_sent": r["LastSentDate"],
            "last_success": bool(r["LastSentSuccess"])}


def save(data: Dict[str, Any]) -> Dict[str, Any]:
    port = int(data.get("port") or 587)
    if not 1 <= port <= 65535:
        raise SmtpError("Port SMTP invalide.")
    schedule = data.get("schedule") or "Aucun"
    if schedule not in ("Aucun", "Hebdomadaire", "Mensuel"):
        raise SmtpError("Envoi programmé : Aucun, Hebdomadaire ou Mensuel.")
    values = {"Server": (data.get("server") or "").strip()[:200], "Port": port, "Username": (data.get("username") or "").strip()[:200],
              "RecipientEmail": (data.get("recipient") or "").strip()[:500], "ScheduleType": schedule}
    password = data.get("password")
    if password:
        if not dpapi.is_available():
            raise SmtpError("Stockage chiffré (DPAPI) indisponible sur ce poste : mot de passe non enregistré.")
        values["Password"] = dpapi.protect(password)
    with unified_db.connect() as conn:
        r = conn.execute("SELECT Id FROM SmtpSettings ORDER BY Id LIMIT 1").fetchone()
        if r is None:
            unified_db.insert(conn, "SmtpSettings", "SmtpSettings", {**values, "Password": values.get("Password", ""), "LastSentSuccess": 0})
        else:
            unified_db.update(conn, "SmtpSettings", "SmtpSettings", r["Id"], values)
    return get()


def send_test(to: str = "") -> str:
    with unified_db.connect() as conn:
        r = conn.execute("SELECT * FROM SmtpSettings ORDER BY Id LIMIT 1").fetchone()
    if r is None or not r["Server"]:
        raise SmtpError("Renseignez d'abord le serveur SMTP.")
    recipient = (to or r["RecipientEmail"] or "").split(",")[0].strip()
    if "@" not in recipient:
        raise SmtpError("Indiquez un destinataire.")
    password = dpapi.unprotect(r["Password"]) if r["Password"] else ""
    msg = EmailMessage()
    msg["Subject"] = "AFMI Smart Admin — message de test"
    msg["From"] = r["Username"] or recipient
    msg["To"] = recipient
    msg.set_content("Ce message confirme que l'envoi d'e-mails depuis AFMI Smart Admin fonctionne.")
    context = ssl.create_default_context()
    try:
        if r["Port"] == 465:
            with smtplib.SMTP_SSL(r["Server"], r["Port"], context=context, timeout=20) as s:
                if r["Username"]:
                    s.login(r["Username"], password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(r["Server"], r["Port"], timeout=20) as s:
                s.starttls(context=context)              # jamais d'identifiants en clair sur le réseau
                if r["Username"]:
                    s.login(r["Username"], password)
                s.send_message(msg)
    except (OSError, smtplib.SMTPException) as e:
        raise SmtpError(f"Envoi impossible : {e}") from e
    return recipient
