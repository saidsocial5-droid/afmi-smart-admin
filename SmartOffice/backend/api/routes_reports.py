"""API des rapports annuels (Lot 5), des indicateurs GAR et de leurs mesures."""
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from backend.core import unified_db
from backend.tools.editor import photos
from backend.tools.reports import generator

router = APIRouter(tags=["Rapports annuels"])
LEVELS = ("Impact", "Effet", "Extrant")
AGGREGATIONS = ("Somme", "Dernière")


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Enregistrement refusé par la base : {e}")


@router.get("/api/reports/context")
def context():
    def load():
        with unified_db.connect() as conn:
            years = {int(r[0][:4]) for r in conn.execute("SELECT DISTINCT substr(OperationDate, 1, 4) FROM Operations WHERE IsDeleted = 0")}
            years |= {r[0] for r in conn.execute("SELECT Year FROM FiscalYears")}
            years |= {int(str(r[0])[:4]) for r in conn.execute("SELECT DISTINCT ActivityDate FROM ActivityReports") if r[0]}
            return {
                "years": sorted(years, reverse=True),
                "projects": [dict(id=r["Id"], code=r["Code"], name=r["Name"], parent_id=r["ParentProjectId"],
                                  has_children=bool(conn.execute("SELECT 1 FROM Projects WHERE ParentProjectId = ? AND IsDeleted = 0", (r["Id"],)).fetchone()))
                             for r in conn.execute("SELECT * FROM Projects WHERE IsDeleted = 0 ORDER BY Code")],
                "funders": [dict(id=r["Id"], name=r["Name"]) for r in conn.execute("SELECT Id, Name FROM Funders ORDER BY Name")],
                "templates": [dict(id=r["Id"], name=r["Name"]) for r in conn.execute("SELECT Id, Name FROM DocumentTemplates WHERE IsDeleted = 0 ORDER BY Name")],
            }
    return _guard(load)


@router.post("/api/reports/checks")
def checks(data: Dict[str, Any]):
    return _guard(generator.run_checks, int(data["year"]), data.get("scope_type", "association"), data.get("scope_id"))


@router.post("/api/reports/generate")
async def generate(data: Dict[str, Any]):
    try:
        result = await generator.generate(int(data["year"]), data.get("scope_type", "association"), data.get("scope_id"),
                                          data.get("language", "fr"), data.get("kind", "both"), data.get("template_id"),
                                          bool(data.get("use_ai")), bool(data.get("accept_warnings", True)))
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e).strip("'"))
    except unified_db.UnifiedDbUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    if result["document"] is None:
        raise HTTPException(status_code=409, detail={"message": "Contrôles de cohérence bloquants : corrigez-les avant de générer le rapport.",
                                                     "checks": result["checks"]})
    return result


@router.get("/api/reports/table/{name}")
def table(name: str, year: int, scope_type: str = "association", scope_id: Optional[int] = None, lang: str = "fr"):
    return _guard(generator.table, name, year, scope_type, scope_id, lang)


# --- Indicateurs GAR et mesures désagrégées ---------------------------------------------------------------

@router.get("/api/indicators")
def list_indicators(project_id: int):
    def load():
        with unified_db.connect() as conn:
            out = []
            for i in conn.execute("SELECT * FROM Indicators WHERE ProjectId = ? ORDER BY Name", (project_id,)):
                ms = [dict(id=m["Id"], period_end=m["PeriodEnd"], value=m["Value"], sex=m["Sex"], age_group=m["AgeGroup"], zone=m["Zone"],
                           source=m["Source"], notes=m["Notes"])
                      for m in conn.execute("SELECT * FROM IndicatorMeasurements WHERE IndicatorId = ? ORDER BY PeriodEnd DESC, Id DESC", (i["Id"],))]
                out.append(dict(id=i["Id"], name=i["Name"], description=i["Description"], unit=i["Unit"], target=i["TargetValue"],
                                current=i["CurrentValue"], level=i["Level"], baseline=i["BaselineValue"], aggregation=i["Aggregation"], measurements=ms))
            return out
    return _guard(load)


@router.post("/api/indicators")
def save_indicator(data: Dict[str, Any]):
    def save():
        if data.get("level", "Extrant") not in LEVELS or data.get("aggregation", "Somme") not in AGGREGATIONS:
            raise ValueError("Niveau (Impact, Effet, Extrant) ou mode de cumul (Somme, Dernière) invalide.")
        if not (data.get("name") or "").strip():
            raise ValueError("Nom de l'indicateur obligatoire.")
        values = {"Name": data["name"].strip(), "Description": data.get("description", ""), "Unit": data.get("unit", ""),
                  "TargetValue": float(data.get("target") or 0), "Level": data.get("level", "Extrant"),
                  "BaselineValue": None if data.get("baseline") in (None, "") else float(data["baseline"]),
                  "Aggregation": data.get("aggregation", "Somme")}
        with unified_db.connect() as conn:
            if data.get("id"):
                unified_db.update(conn, "Indicators", "Indicator", data["id"], values)
                return {"id": data["id"]}
            return {"id": unified_db.insert(conn, "Indicators", "Indicator", {**values, "CurrentValue": 0, "ProjectId": int(data["project_id"])})}
    return _guard(save)


@router.post("/api/indicators/{indicator_id}/measurements")
def add_measurement(indicator_id: int, data: Dict[str, Any]):
    def add():
        sex = (data.get("sex") or "").upper()
        if sex not in ("", "F", "M"):
            raise ValueError("Sexe : F, M ou vide.")
        with unified_db.connect() as conn:
            mid = unified_db.insert(conn, "IndicatorMeasurements", "IndicatorMeasurement", {
                "IndicatorId": indicator_id, "PeriodEnd": data["period_end"], "Value": float(data["value"]), "Sex": sex,
                "AgeGroup": (data.get("age_group") or "")[:30], "Zone": (data.get("zone") or "")[:100], "Source": (data.get("source") or "")[:200],
                "Notes": data.get("notes", ""), "CreatedAtUtc": unified_db.now_ef()})
            # La valeur courante de l'indicateur (affichée dans l'application de bureau) suit le cumul de toutes les mesures non désagrégées.
            agg = conn.execute("SELECT Aggregation FROM Indicators WHERE Id = ?", (indicator_id,)).fetchone()["Aggregation"]
            ms = [dict(m) for m in conn.execute("SELECT * FROM IndicatorMeasurements WHERE IndicatorId = ?", (indicator_id,))]
            from backend.tools.reports.moral import _aggregate
            current = _aggregate(ms, agg)
            if current is not None:
                unified_db.update(conn, "Indicators", "Indicator", indicator_id, {"CurrentValue": current})
            return {"id": mid}
    return _guard(add)


@router.delete("/api/indicators/{indicator_id}/measurements/{measurement_id}")
def delete_measurement(indicator_id: int, measurement_id: int):
    def delete():
        with unified_db.connect() as conn:
            unified_db.hard_delete(conn, "IndicatorMeasurements", "IndicatorMeasurement", measurement_id)
        return {"status": "deleted"}
    return _guard(delete)


@router.post("/api/photos/import-legacy")
def import_legacy_photos():
    return _guard(photos.import_legacy_activity_photos)
