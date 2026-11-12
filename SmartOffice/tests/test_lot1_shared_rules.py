import json
from datetime import datetime
from pathlib import Path

import pytest

from backend.core.unified_db import compute_audit_hash, _hash_datetime
from backend.tools import rib

SHARED = Path(__file__).resolve().parents[2] / "SharedTestCases"


def _cases(name):
    return json.loads((SHARED / name).read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _cases("rib.json"), ids=lambda c: c["input"] or "vide")
def test_rib_matches_shared_vectors(case):
    result = rib.check(case["input"])
    assert result.is_well_formed == case["wellFormed"]
    assert result.is_key_valid == case["keyValid"]


@pytest.mark.parametrize("case", _cases("audit_hash.json"))
def test_audit_hash_matches_shared_vectors(case):
    assert compute_audit_hash(case["previousHash"], case["timestampUtc"], case["user"], case["machine"],
                              case["entityType"], case["entityId"], case["action"], case["changesJson"]) == case["expectedHash"]


def test_hash_timestamp_format_matches_dotnet():
    assert _hash_datetime(datetime(2026, 11, 10, 12, 34, 56, 123456)) == "2026-11-10T12:34:56.1234560"
    assert _hash_datetime(datetime(2026, 1, 1)) == "2026-01-01T00:00:00.0000000"
