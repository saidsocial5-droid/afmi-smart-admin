# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Development Commands

### Running the Application
- **Unified Launcher (Backend + Frontend):** `python run_app.py`
- **Web-only Mode:** `python run_app.py --web-only`
- **Desktop Mode (Windows):** Run `start_desktop.bat`
- **Web Mode (Windows):** Run `start_web.bat`

### Decoupled Development (recommended for active development)
```bash
# Terminal 1 – Backend FastAPI with hot-reload
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 – Frontend Vite dev server (http://localhost:5173)
cd frontend && npm run dev
```

### Frontend Build & Package
```bash
cd frontend && npm run build          # production web build → frontend/dist/
cd frontend && npm run electron:build # Electron desktop installer
cd frontend && npm run electron:dev   # Electron + Vite in parallel (dev mode)
```

### Environment Variables (no .env file — set in shell before launch)
| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | Active LLM backend (`gemini` or `ollama`) |
| `GEMINI_API_KEY` | *(required for Gemini)* | Google AI Studio key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model ID |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_MODEL` | `llama3.1` | Text model for Ollama |
| `OLLAMA_VISION_MODEL` | `llama3.2-vision` | Vision model for scanned-document OCR |

There is no `requirements.txt` in the repo. Install backend dependencies manually; the key packages are `fastapi`, `uvicorn`, `sqlalchemy`, `pdfplumber`, `pymupdf`, `pillow`, `httpx`, and `python-docx`.

## 🏛️ Architecture & Structure

### Request Flow
```
Browser / Electron renderer
    → frontend/src/apiClient.js   (REST calls to backend)
    → backend/api/routes_*.py     (FastAPI routers)
    → backend/core/               (agents, LLM routing, DB)
    → backend/tools/              (OCR, export, grant scanner)
    → backend/plugins/            (domain-specific extensions)
```

### Backend Core (`/backend/core`)
- **`llm_router.py`** – Singleton `llm_router` used by every agent. Routes text/vision calls to either Google Gemini (via `httpx` against the REST API) or a local Ollama server. Falls back to a structured heuristic parser when Ollama is unreachable.
- **`base_agent.py`** – Abstract `BaseAgent` class. Each agent loads its `system_prompt`, `temperature`, `model_provider`, and `active_tools` from SQLite on init so they are configurable at runtime from the Agent Studio UI without a redeploy. Tools are registered with `register_tool()`.
- **`agent_registry.py`** – Discovers and instantiates all agents. Plugins in `backend/plugins/` are loaded dynamically here; adding a new `*_plugin.py` file is enough to extend the system.
- **`database.py`** – SQLite schema via SQLAlchemy. `init_db()` is called at FastAPI startup and seeds the four default agents.

### Agents (`/backend/api/routes_agents.py`)
Four concrete agents, each extending `BaseAgent`:
- `AgentGrantWriter` – logframe generation, DOCX export, carbon offset tool
- `AgentProjectManager` – KPI calculation, risk matrix, M&E support
- `AgentFinanceAuditor` – OCR parsing, ICE validation, Excel ledger export
- `AgentCommunications` – press releases, social media, bilingual newsletters

Agent configs (prompts, temperature, model) live in SQLite and are editable via `AgentStudioView`. The `ngo_profile.json` institutional memory is injected into every agent's system prompt context automatically via `BaseAgent._load_ngo_profile()`.

### OCR Engine (`/backend/tools/ocr_engine.py`)
Two-path pipeline:
1. **Digital PDFs** → `pdfplumber` / `PyMuPDF` for precise vector text/table extraction.
2. **Scanned images & image-PDFs** → Multimodal Vision AI (Gemini 2.5 Flash or `llama3.2-vision`) with a structured JSON fallback heuristic.

Moroccan-specific logic: automatic bank detection (Banque Populaire, Attijariwafa, BMCE, CIH, CAM), RIB validation (24 digits), ICE validation (15 digits), TVA rate checking (20% standard + reduced rates).

### Plugin System (`/backend/plugins/`)
Drop a `*_plugin.py` file here; `agent_registry.py` loads it automatically. Each plugin registers new tools into the relevant agents. Existing plugins: `carbon_calculator_plugin.py` and `morocco_procurement_plugin.py`.

### Frontend (`/frontend/src`)
- **`apiClient.js`** – Centralised Axios/fetch wrapper. The backend URL is resolved from Electron's `window.__BACKEND_PORT__` (set via `preload.cjs`) or defaults to `http://localhost:8000`.
- **`context/LanguageContext.jsx`** – Global Arabic/French toggle; drives `dir="rtl"` on the document root. All views must respect RTL layout.
- **`i18n.js`** – Translation strings; extend here when adding new UI text.
- **Views** are self-contained modules: each owns its own API calls, local state, and export logic.

### Electron Integration (`/frontend/electron/`)
- **`main.cjs`** – Reads `backend/data/.backend_port` to know which port the Python process bound to, then injects it into the renderer via `preload.cjs`. Handles window lifecycle and auto-launches the backend when started via `start_desktop.bat`.
- **`preload.cjs`** – Context-isolated bridge; exposes `window.__BACKEND_PORT__` to the renderer. Add new IPC channels here, never by disabling `contextIsolation`.

### Institutional Memory (`/backend/config/ngo_profile.json`)
Shared context injected into all AI prompts. Contains legal identifiers (ICE, RIB), strategic axes, target donors, budget rules (MAD currency, overhead limits, TVA rates). Edit through `InstitutionalMemoryView` in the UI or directly in the file — changes take effect on the next agent request without restart.

## 🔑 Key Conventions

- **No test framework is configured.** When adding tests, use `pytest` for the backend and Vitest for the frontend.
- **Agent tool registration** follows the pattern in `BaseAgent.register_tool()` — each tool is a plain async function with a `description` string and a `parameters` dict (JSON-Schema style).
- **All AI responses** must handle the `gemini` / `ollama` split; use `llm_router.generate()` (text) or `llm_router.generate_vision()` (multimodal), never call provider SDKs directly from routes or agents.
- **RTL-first UI**: Tailwind classes for spacing/alignment that assume LTR (`ml-*`, `mr-*`, `text-left`) should use logical variants (`ms-*`, `me-*`, `text-start`) so Arabic and French layouts both render correctly.
- **Institutional colours** — Forest Green `#1B4332`, Terracotta/Gold `#D4A373`, Slate White `#F8F9FA`. Use these when adding new UI components.
