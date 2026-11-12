"""Registre des paramètres de l'application (Lot 7) : une seule description pour l'écran, la validation, la
recherche, l'import/export JSON et le retour aux valeurs par défaut.

Chaque paramètre est une ligne de la table AppSettings (valeur JSON) partagée avec l'application de bureau.
Un paramètre absent de la table vaut sa valeur par défaut ; « Restaurer la valeur par défaut » supprime la ligne
(trace dans le journal d'audit). Les secrets (clés d'API) sont chiffrés par DPAPI et ne sont jamais exportés.
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core import ai_config, unified_db

ROLES = {
    "Administrateur": "Tous les droits, dont les paramètres, les utilisateurs et les sauvegardes.",
    "Comptable": "Trésorerie, relevés, paie, rapports, éditeur et GED ; pas les paramètres.",
    "Chargé de projet": "Projets, éditeur, GED, indicateurs, photos et rapports ; pas la trésorerie ni la paie.",
    "Lecteur": "Consultation et exports uniquement.",
}


@dataclass
class Field:
    key: str
    section: str
    label: str
    type: str                       # bool, int, float, string, text, select, json, secret, color, users
    default: Any = None
    help: str = ""
    options: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    group: str = ""
    restart: bool = False           # pris en compte au prochain démarrage de l'application de bureau

    def public(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != ""}


SECTIONS = [
    ("association", "Association", "Identité, exercices, devise et langue"),
    ("comptabilite", "Comptabilité", "Catégories, règles de classement, seuils"),
    ("banques", "Banques", "Rapprochement, gabarits de relevés, alertes et anomalies"),
    ("chartes", "Chartes et modèles", "Mise en page par défaut des documents"),
    ("exports", "Exports", "Nommage des fichiers, moteur PDF, PDF/A"),
    ("ia", "Intelligence artificielle", "Fournisseur par tâche, clés, coûts, confidentialité, prompts"),
    ("notifications", "Notifications", "Messagerie (SMTP) et alertes envoyées"),
    ("utilisateurs", "Utilisateurs et rôles", "Comptes Windows autorisés et leurs droits"),
    ("sauvegardes", "Sauvegardes", "Dossier, fréquence, conservation, restauration"),
    ("apparence", "Apparence", "Langue de l'interface, taille du texte, couleur principale"),
    ("rapports", "Rapports et cycle de vie", "Niveaux des contrôles, documents attendus par phase"),
    ("mises_a_jour", "Mises à jour", "Recherche automatique des nouvelles versions"),
]

MONTHS = list(range(1, 13))
FIELDS: List[Field] = [
    # Association
    Field("association.name", "association", "Nom de l'association", "string", "Association Forêt Modèle d'Ifrane"),
    Field("association.acronym", "association", "Sigle", "string", "AFMI", "Utilisé dans le nom des fichiers exportés ({org})."),
    Field("association.address", "association", "Adresse", "text", ""),
    Field("association.fiscal_year_start_month", "association", "Premier mois de l'exercice", "select", 1, options=MONTHS,
          help="1 = janvier. Les exercices déjà créés ne sont pas modifiés."),
    Field("association.default_currency", "association", "Devise par défaut", "select", "MAD", options=["MAD", "EUR", "USD"],
          help="Les montants en devise sont convertis avec les taux datés (Trésorerie › Taux)."),
    Field("association.default_language", "association", "Langue par défaut des rapports", "select", "fr", options=["fr", "ar", "en"]),
    # Comptabilité
    Field("accounting.receipt_threshold_mad", "comptabilite", "Seuil de justificatif obligatoire (MAD)", "float", 1000, min=0,
          help="Une dépense égale ou supérieure sans pièce jointe est signalée (relevés, contrôles des rapports)."),
    Field("accounting.auto_learn_rules", "comptabilite", "Apprendre les règles de classement des relevés validés", "bool", True,
          help="Le libellé d'une ligne validée devient une règle de suggestion (catégorie, projet, ligne)."),
    # Banques
    Field("bank.reconciliation_tolerance_days", "banques", "Tolérance de date du rapprochement automatique (jours)", "int", 3, min=0, max=30,
          help="Écart maximal entre la date du relevé et celle de l'opération (écran Trésorerie et relevés importés)."),
    Field("bank.fee_alert_min_mad", "banques", "Seuil des frais bancaires inhabituels (MAD)", "float", 500, min=0,
          help="Frais sans historique au-delà duquel une anomalie est signalée à l'import d'un relevé."),
    Field("bank.ocr_auto_ai", "banques", "Proposer la lecture par l'IA quand l'OCR ne s'équilibre pas", "bool", True),
    # Chartes
    Field("charts.default_template_id", "chartes", "Modèle de document par défaut (identifiant)", "int", None, min=1,
          help="Laissez vide : document vierge. Les chartes se gèrent dans « Chartes et modèles »."),
    # Exports
    Field("exports.naming.report", "exports", "Nom des rapports et états", "string", "{org}_{type}_{year}_{lang}",
          help="Variables : {org} {type} {year} {lang} {project} {date}. Exemple : AFMI_RapportFinancier_2026_FR.pdf"),
    Field("exports.naming.document", "exports", "Nom des documents de l'éditeur", "string", "{org}_{title}_{date}",
          help="Variables : {org} {title} {project} {date} {lang}."),
    Field("exports.pdf_engine", "exports", "Moteur PDF", "select", "auto", options=["auto", "browser", "libreoffice"],
          help="auto : navigateur (Edge) ; LibreOffice si installé pour les notes en bas de page et le PDF/A."),
    Field("exports.pdfa_default", "exports", "Proposer le PDF/A par défaut", "bool", False),
    # IA — confidentialité et coûts
    Field("ai.offline_mode", "ia", "Mode hors ligne (aucun appel à une IA externe)", "bool", True, group="Confidentialité"),
    Field("ai.mask_sensitive_data", "ia", "Masquer RIB, CIN, salaires… avant tout envoi externe", "bool", True, group="Confidentialité",
          help="Une image (relevé, facture) ne pouvant être masquée, elle n'est alors jamais envoyée à l'extérieur."),
    Field("ai.cost.monthly_cap", "ia", "Plafond de coût mensuel (USD)", "float", 0, min=0, group="Coûts",
          help="0 = pas de plafond. Le coût est estimé avec les prix saisis par fournisseur ; au plafond, le moteur local prend le relais."),
]
for _p, _meta in ai_config.PROVIDERS.items():
    if _p == "heuristic":
        continue
    FIELDS.append(Field(f"ai.providers.{_p}", "ia", f"{_meta['label']} — réglages", "json",
                        {"base_url": _meta["base_url"], "model": _meta["model"], "price_in": 0, "price_out": 0}, group="Fournisseurs",
                        help="URL, modèle par défaut, prix par million de jetons (entrée, sortie) en USD."))
    if _meta["external"] is not False:
        FIELDS.append(Field(f"ai.keys.{_p}", "ia", f"{_meta['label']} — clé d'API", "secret", None, group="Fournisseurs",
                            help="Chiffrée par DPAPI (compte Windows) ; jamais exportée ni affichée."))
for _t, _meta in ai_config.TASKS.items():
    FIELDS.append(Field(f"ai.tasks.{_t}", "ia", _meta["label"], "json", dict(ai_config.TASK_DEFAULT), group="Fournisseur par tâche",
                        help="Fournisseur (auto = comportement par défaut), modèle, température, limite de jetons."))
for _n, _meta in ai_config.PROMPTS.items():
    FIELDS.append(Field(f"ai.prompts.{_n}", "ia", _meta["label"], "text", _meta["text"], group="Prompts système"))
FIELDS += [
    # Notifications (le serveur SMTP lui-même est géré par la table SmtpSettings, voir routes)
    Field("notifications.recipients", "notifications", "Destinataires des alertes", "string", "",
          help="Adresses séparées par des virgules."),
    Field("notifications.events", "notifications", "Alertes envoyées par e-mail", "json",
          {"obligations": True, "treasury": True, "reconciliation": False, "backup_failure": True},
          help="Échéances des bailleurs, trésorerie, relevés non rapprochés, échec de sauvegarde. Vérifiées toutes les heures ; un récapitulatif est envoyé dès qu'une alerte nouvelle apparaît (rappel après 7 jours)."),
    # Utilisateurs
    Field("security.users", "utilisateurs", "Utilisateurs autorisés", "users", [],
          help="Liste vide : poste mono-utilisateur, tous les droits. Sinon, un compte Windows absent de la liste n'a qu'un accès en lecture."),
    # Sauvegardes
    Field("backup.folder", "sauvegardes", "Dossier des sauvegardes", "string", "",
          help="Vide : dossier « Backups » à côté de la base. Un disque externe ou un dossier synchronisé est recommandé.", restart=True),
    Field("backup.frequency", "sauvegardes", "Fréquence", "select", "daily", options=["startup", "daily", "weekly", "manual"],
          help="Vérifiée au démarrage de l'application de bureau et toutes les heures.", restart=True),
    Field("backup.retention", "sauvegardes", "Nombre de sauvegardes conservées", "int", 30, min=1, max=365),
    # Documents (Lot 9)
    Field("ged.mirror_local", "rapports", "Copier chaque document dans les dossiers locaux du projet", "bool", True, group="Documents",
          help="Structure des « Dossiers Locaux » : Année › Trimestre › Comptes rendus, Rapports d'avancement, Rapports financiers."),
    Field("ged.local_root", "rapports", "Dossier racine des projets", "string", "", group="Documents",
          help="Vide : Documents\\AFMI_Projets. Utilisé quand un projet n'a pas encore de dossier local."),
    # Cofinancement (Lot 10)
    Field("cofinancing.account_use", "comptabilite", "Compte d'emploi des contributions en nature", "string",
          "86 — Emplois des contributions volontaires en nature", group="Contributions en nature",
          help="Utilisé pour les bailleurs réglés sur « Comptabilité » : écriture de valorisation équilibrée, sans effet sur le résultat "
               "ni sur la trésorerie. Comptes 86 / 87 confirmés par l'association (modifiables)."),
    Field("cofinancing.account_source", "comptabilite", "Compte de ressource des contributions en nature", "string",
          "87 — Contributions volontaires en nature", group="Contributions en nature"),
    # Mises à jour
    Field("updates.auto_check", "mises_a_jour", "Rechercher automatiquement les nouvelles versions au démarrage", "bool", True,
          help="L'application de bureau consulte la dernière version publiée (manifeste signé). Rien n'est installé sans votre accord : "
               "un bandeau propose « Installer maintenant ». Seule la version installée est envoyée par la requête, aucune donnée."),
    # Apparence
    Field("ui.language", "apparence", "Langue de l'interface", "select", "fr", options=["fr", "ar"]),
    Field("ui.font_scale", "apparence", "Taille du texte (%)", "int", 100, min=85, max=130),
    Field("ui.primary_color", "apparence", "Couleur principale de l'interface", "color", "#1B4332"),
]
BY_KEY = {f.key: f for f in FIELDS}
CONFIG_FILES = {
    "financial_report_layout": "Présentation des états financiers et niveaux des contrôles des rapports",
    "lifecycle_config": "Documents attendus par phase du cycle de vie",
    "bank_templates": "Gabarits de lecture des relevés par banque",
}


class SettingsError(ValueError):
    pass


def validate(f: Field, value: Any) -> Any:
    """Valeur normalisée ou SettingsError (message en français)."""
    if value is None:
        if f.type in ("int", "float") and f.default is None:
            return None
        raise SettingsError(f"{f.label} : valeur obligatoire.")
    try:
        if f.type == "bool":
            if not isinstance(value, bool):
                raise SettingsError(f"{f.label} : oui ou non attendu.")
        elif f.type == "int":
            if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
                raise SettingsError(f"{f.label} : nombre entier attendu.")
            value = int(value)
        elif f.type == "float":
            if isinstance(value, bool):
                raise SettingsError(f"{f.label} : nombre attendu.")
            value = float(value)
        elif f.type in ("string", "text"):
            if not isinstance(value, str):
                raise SettingsError(f"{f.label} : texte attendu.")
            if f.type == "string" and len(value) > 500:
                raise SettingsError(f"{f.label} : 500 caractères au plus.")
        elif f.type == "color":
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                raise SettingsError(f"{f.label} : couleur #RRVVBB attendue.")
        elif f.type == "select":
            if value not in f.options:
                raise SettingsError(f"{f.label} : valeur parmi {', '.join(map(str, f.options))}.")
        elif f.type == "json":
            if not isinstance(value, type(f.default)):
                raise SettingsError(f"{f.label} : structure invalide.")
            value = _validate_json(f, value)
        elif f.type == "users":
            value = _validate_users(value)
        elif f.type == "secret":
            raise SettingsError(f"{f.label} : utilisez l'enregistrement des clés.")
    except (TypeError, ValueError) as e:
        if isinstance(e, SettingsError):
            raise
        raise SettingsError(f"{f.label} : valeur invalide.") from e
    if f.min is not None and isinstance(value, (int, float)) and value < f.min:
        raise SettingsError(f"{f.label} : minimum {f.min:g}.")
    if f.max is not None and isinstance(value, (int, float)) and value > f.max:
        raise SettingsError(f"{f.label} : maximum {f.max:g}.")
    return value


def _validate_json(f: Field, value: Dict[str, Any]) -> Dict[str, Any]:
    if f.key.startswith("ai.tasks."):
        out = {**ai_config.TASK_DEFAULT, **{k: value.get(k) for k in ai_config.TASK_DEFAULT if k in value}}
        if out["provider"] not in ("auto", *ai_config.PROVIDERS):
            raise SettingsError(f"{f.label} : fournisseur inconnu.")
        if out["temperature"] not in (None, "") and not 0 <= float(out["temperature"]) <= 2:
            raise SettingsError(f"{f.label} : température de 0 à 2.")
        if out["max_tokens"] not in (None, "") and not 1 <= int(out["max_tokens"]) <= 200_000:
            raise SettingsError(f"{f.label} : limite de jetons de 1 à 200 000.")
        out["temperature"] = None if out["temperature"] in (None, "") else float(out["temperature"])
        out["max_tokens"] = None if out["max_tokens"] in (None, "") else int(out["max_tokens"])
        out["model"] = str(out["model"] or "")[:120]
        if ai_config.TASKS[f.key.split(".")[-1]]["vision"] is False:
            pass
        return out
    if f.key.startswith("ai.providers."):
        url = str(value.get("base_url") or f.default["base_url"])
        if url and not re.match(r"^https?://", url):
            raise SettingsError(f"{f.label} : l'adresse doit commencer par http:// ou https://.")
        provider = f.key.split(".")[-1]
        if ai_config.PROVIDERS[provider]["external"] is True and not url.startswith("https://"):
            raise SettingsError(f"{f.label} : un fournisseur en ligne doit être joint en https.")
        prices = [float(value.get("price_in") or 0), float(value.get("price_out") or 0)]
        if min(prices) < 0:
            raise SettingsError(f"{f.label} : prix positifs attendus.")
        return {"base_url": url, "model": str(value.get("model") or "")[:120], "price_in": prices[0], "price_out": prices[1]}
    if f.key == "notifications.events":
        return {k: bool(value.get(k, v)) for k, v in f.default.items()}
    return value


def _validate_users(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        raise SettingsError("Utilisateurs : liste attendue.")
    out, seen = [], set()
    for u in value:
        login = str((u or {}).get("login") or "").strip()
        if not login:
            raise SettingsError("Utilisateurs : identifiant Windows obligatoire.")
        if login.lower() in seen:
            raise SettingsError(f"Utilisateurs : « {login} » figure deux fois.")
        seen.add(login.lower())
        role = u.get("role") or "Lecteur"
        if role not in ROLES:
            raise SettingsError(f"Utilisateurs : rôle inconnu « {role} ».")
        out.append({"login": login[:100], "name": str(u.get("name") or "")[:150], "role": role, "active": bool(u.get("active", True))})
    if out and not any(u["role"] == "Administrateur" and u["active"] for u in out):
        raise SettingsError("Utilisateurs : il faut au moins un administrateur actif.")
    me = unified_db.current_user().lower()
    if out and not any(u["login"].lower() == me and u["role"] == "Administrateur" and u["active"] for u in out):
        raise SettingsError(f"Utilisateurs : votre propre compte ({unified_db.current_user()}) doit rester administrateur actif, "
                            "sinon vous perdriez l'accès aux paramètres.")
    return out


# --- Lecture et écriture ---------------------------------------------------------------------------------------

def _stored() -> Dict[str, Any]:
    with unified_db.connect() as conn:
        return {r["Key"]: (r["ValueJson"], bool(r["IsSecret"]), r["UpdatedAtUtc"]) for r in conn.execute("SELECT * FROM AppSettings")}


def snapshot() -> Dict[str, Any]:
    """Sections et paramètres avec leur valeur courante (les secrets : seulement « configuré » ou non)."""
    stored = _stored()
    out = []
    for sid, label, desc in SECTIONS:
        fields = []
        for f in (x for x in FIELDS if x.section == sid):
            row = stored.get(f.key)
            item = f.public()
            if f.type == "secret":
                item["configured"] = bool(row and json.loads(row[0]))
                item["value"] = None
            else:
                item["value"] = json.loads(row[0]) if row else f.default
                if f.type == "json" and isinstance(f.default, dict) and isinstance(item["value"], dict):
                    item["value"] = {**f.default, **item["value"]}
            item["is_default"] = row is None
            item["updated_at"] = row[2] if row else None
            fields.append(item)
        out.append({"id": sid, "label": label, "description": desc, "fields": fields})
    return {"sections": out, "roles": ROLES, "config_files": CONFIG_FILES, "current_user": unified_db.current_user()}


def get(key: str) -> Any:
    f = BY_KEY[key]
    v = unified_db.get_setting(key, None)
    return f.default if v is None else v


def save(values: Dict[str, Any]) -> Dict[str, Any]:
    """Valide tout puis enregistre (rien n'est écrit si une valeur est invalide)."""
    clean = {}
    errors = []
    for key, value in values.items():
        f = BY_KEY.get(key)
        if f is None:
            errors.append(f"Paramètre inconnu : {key}.")
            continue
        try:
            clean[key] = validate(f, value)
        except SettingsError as e:
            errors.append(str(e))
    if errors:
        raise SettingsError(" ".join(errors))
    for key, value in clean.items():
        unified_db.set_setting(key, value)
    return clean


def set_secret(key: str, value: str) -> None:
    f = BY_KEY.get(key)
    if f is None or f.type != "secret":
        raise SettingsError("Clé de secret inconnue.")
    value = (value or "").strip()
    if not value:
        reset([key])
        return
    from backend.core import dpapi
    if not dpapi.is_available():
        raise SettingsError("Stockage chiffré (DPAPI) indisponible sur ce poste : la clé n'est pas enregistrée.")
    unified_db.set_setting(key, value, secret=True)


def reset(keys: List[str]) -> int:
    """Retour aux valeurs par défaut : suppression des lignes (tracée dans le journal d'audit)."""
    unknown = [k for k in keys if k not in BY_KEY]
    if unknown:
        raise SettingsError(f"Paramètre inconnu : {', '.join(unknown)}.")
    n = 0
    with unified_db.connect() as conn:
        for key in keys:
            row = conn.execute("SELECT IsSecret FROM AppSettings WHERE Key = ?", (key,)).fetchone()
            if row is None:
                continue
            if key == "security.users":
                pass                                             # liste vide = poste mono-utilisateur
            conn.execute("DELETE FROM AppSettings WHERE Key = ?", (key,))
            unified_db.append_audit(conn, "AppSetting", key, unified_db.ACTION_DELETE, {"reset": "valeur par défaut"})
            n += 1
    return n


def section_keys(section: str) -> List[str]:
    return [f.key for f in FIELDS if f.section == section]


def export_json() -> Dict[str, Any]:
    """Paramètres modifiés (secrets exclus) et fichiers de configuration personnalisés."""
    from backend.core import config_files
    stored = _stored()
    values = {k: json.loads(v[0]) for k, v in stored.items() if k in BY_KEY and not v[1] and BY_KEY[k].type != "secret"}
    return {"format": "afmi-settings", "version": 1, "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "exported_by": unified_db.current_user(), "values": values,
            "files": {name: config_files.read(name) for name in CONFIG_FILES if config_files.is_customized(name)},
            "note": "Les clés d'API ne sont jamais exportées : ressaisissez-les sur le poste de destination."}


def import_json(data: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    from backend.core import config_files
    if not isinstance(data, dict) or data.get("format") != "afmi-settings":
        raise SettingsError("Fichier non reconnu : export de paramètres AFMI attendu.")
    values = data.get("values") or {}
    skipped = [k for k in values if k in BY_KEY and BY_KEY[k].type == "secret"]
    values = {k: v for k, v in values.items() if k not in skipped and not k.startswith("ai.usage.")}
    files = data.get("files") or {}
    errors = []
    clean = {}
    for key, value in values.items():
        f = BY_KEY.get(key)
        if f is None:
            errors.append(f"Paramètre inconnu : {key}.")
            continue
        try:
            clean[key] = validate(f, value)
        except SettingsError as e:
            errors.append(str(e))
    for name, content in files.items():
        try:
            config_files.validate(name, content)
        except ValueError as e:
            errors.append(str(e))
    if errors:
        raise SettingsError("Import refusé, rien n'a été modifié : " + " ".join(errors))
    if not dry_run:
        for key, value in clean.items():
            unified_db.set_setting(key, value)
        for name, content in files.items():
            config_files.write(name, content)
    return {"values": len(clean), "files": len(files), "secrets_skipped": skipped, "dry_run": dry_run}
