import os
import sys
import tempfile
from pathlib import Path

# Isolated data dir: tests never touch the real database. Must be set before importing backend.
_tmp = tempfile.mkdtemp(prefix="afmi_tests_")
os.environ["AFMI_DATA_DIR"] = _tmp
# Jamais la base réelle du poste (%LocalAppData%\AFMIGestionProjet\database.db) : les tests qui en ont besoin
# créent leur propre base unique (tests/unified_db_fixture.py).
os.environ["AFMI_DESKTOP_DB"] = os.path.join(_tmp, "absent_desktop.db")
os.environ.pop("AFMI_API_TOKEN", None)
os.environ["GEMINI_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "heuristic"
os.environ["AFMI_DISABLE_SCHEDULER"] = "1"   # pas d'envoi d'alertes en tâche de fond pendant les tests
os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"  # a local Ollama must not answer during tests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    from backend.main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
def client(app):
    # Context manager runs the startup event (init_db)
    with TestClient(app, base_url="http://127.0.0.1:8000") as c:
        yield c
