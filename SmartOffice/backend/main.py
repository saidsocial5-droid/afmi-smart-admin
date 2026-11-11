import hmac
import os
import re
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config.settings import settings
from backend.core.database import init_db
from backend.api.routes_agents import router as agents_router
from backend.api.routes_ocr import router as ocr_router
from backend.api.routes_finance import router as finance_router
from backend.api.routes_grants import router as grants_router
from backend.api.routes_projects import router as projects_router
from backend.api.routes_settings import router as settings_router, load_persisted_gemini_key
from backend.api.routes_plugins import router as plugins_router
from backend.api.routes_rss import router as rss_router
from backend.api.routes_workflows import router as workflows_router
from backend.api.routes_payroll import router as payroll_router
from backend.api.routes_statements import router as statements_router
from backend.api.routes_editor import router as editor_router
from backend.api.routes_reports import router as reports_router
from backend.api.routes_ged import router as ged_router
from backend.core.orchestrator import mark_interrupted_runs


app = FastAPI(
    title="AFMI-SmartOffice Backend API",
    description="Plateforme Multi-Agents IA & Analyseur OCR Financier pour l'Association Forêt Modèle d'Ifrane",
    version=settings.version
)

# Local-only access: the API has no authentication, so only pages served from this machine
# (the app itself, the WPF WebView2, the Vite dev server) may call it.
LOCAL_ORIGIN_REGEX = r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$"
TOKEN_HEADER = "X-AFMI-Token"
TOKEN_COOKIE = "afmi_session"
TOKEN_QUERY = "afmi_token"
LOCAL_HOST_REGEX = re.compile(r"^(127\.0\.0\.1|localhost)(:\d+)?$", re.IGNORECASE)

@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    # Host check blocks DNS-rebinding; Origin check blocks cross-site requests (CSRF) from any website,
    # including "simple" form POSTs that CORS alone does not stop.
    host = request.headers.get("host", "")
    if not LOCAL_HOST_REGEX.match(host):
        return JSONResponse(status_code=403, content={"detail": "Hôte non autorisé."})
    origin = request.headers.get("origin")
    if origin is not None and not re.match(LOCAL_ORIGIN_REGEX, origin, re.IGNORECASE):
        return JSONResponse(status_code=403, content={"detail": "Origine non autorisée."})

    # Jeton de session (AFMI_API_TOKEN, généré par l'application de bureau à chaque démarrage) : seuls l'application
    # et sa fenêtre Smart Office peuvent appeler l'API, pas les autres programmes du poste. La page est ouverte avec
    # ?afmi_token=… ; le backend pose alors un cookie HttpOnly réutilisé par toutes les requêtes de la page.
    expected = settings.api_token
    if not expected:
        return await call_next(request)
    supplied = request.headers.get(TOKEN_HEADER) or request.cookies.get(TOKEN_COOKIE) or ""
    if hmac.compare_digest(supplied.encode(), expected.encode()):
        return await call_next(request)
    query_token = request.query_params.get(TOKEN_QUERY, "")
    if query_token and hmac.compare_digest(query_token.encode(), expected.encode()):
        response = await call_next(request)
        response.set_cookie(TOKEN_COOKIE, expected, httponly=True, samesite="strict", path="/")
        return response
    return JSONResponse(status_code=401, content={"detail": "Session Smart Office invalide : rouvrez le module depuis l'application."})

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database schema & seed initial data
@app.on_event("startup")
def startup_event():
    print("[AFMI-SmartOffice] Initializing database and agents...")
    init_db()
    mark_interrupted_runs()
    load_persisted_gemini_key()
    print("[AFMI-SmartOffice] System initialized successfully.")

# Mount API Routers
app.include_router(agents_router)
app.include_router(ocr_router)
app.include_router(finance_router)
app.include_router(grants_router)
app.include_router(projects_router)
app.include_router(settings_router)
app.include_router(plugins_router)
app.include_router(rss_router)
app.include_router(workflows_router)
app.include_router(payroll_router)
app.include_router(statements_router)
app.include_router(reports_router)
app.include_router(ged_router)
app.include_router(editor_router)


# Mount exports directory for downloads
app.mount("/exports", StaticFiles(directory=str(settings.exports_dir)), name="exports")

# Mount frontend build if it exists (for unified production deployment)
frontend_dist = settings.frontend_dist_dir
if frontend_dist.exists():
    frontend_dist_root = frontend_dist.resolve()
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Route API introuvable")
        file_path = (frontend_dist / full_path).resolve()
        # Refuse anything that escapes dist/ (e.g. "/../../backend/data/afmi_smartoffice.db")
        if file_path.is_relative_to(frontend_dist_root) and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "app": settings.app_name,
            "title_ar": settings.app_title_ar,
            "status": "Online & Ready",
            "version": settings.version,
            "documentation": "/docs"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
