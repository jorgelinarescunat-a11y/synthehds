"""Tests de la API FastAPI (síncronos sobre el job background)."""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory, monkeypatch_module):
    db_path = tmp_path_factory.mktemp("synth") / "test.db"
    monkeypatch_module.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    # Re-importar tras settear env
    from importlib import reload
    from app.api import storage
    from app import main as main_module
    reload(storage)
    reload(main_module)
    storage.init_db()
    return TestClient(main_module.app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    m = MonkeyPatch()
    yield m
    m.undo()


def _wait_for_job(client, job_id: str, timeout_s: float = 20.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = client.get(f"/api/cohorts/{job_id}/status")
        assert r.status_code == 200
        data = r.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.2)
    pytest.fail(f"Job {job_id} no terminó en {timeout_s}s")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_generate_csv_full_cycle(client):
    r = client.post("/api/cohorts/generate",
                    json={"n_patients": 50, "seed": 1})
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    status = _wait_for_job(client, job_id)
    assert status["status"] == "done", status

    # CSV
    csv_resp = client.get(f"/api/cohorts/{job_id}/data?format=csv")
    assert csv_resp.status_code == 200
    csv_lines = csv_resp.text.strip().splitlines()
    assert len(csv_lines) > 1                  # header + filas

    # Métricas
    m = client.get(f"/api/cohorts/{job_id}/metrics")
    assert m.status_code == 200
    assert "fidelidad_estadistica" in m.json()

    # Preview
    pv = client.get(f"/api/cohorts/{job_id}/preview?limit=5")
    assert pv.status_code == 200
    body = pv.json()
    assert body["n_total"] == 50
    assert len(body["preview"]) == 5

    # FHIR
    fhir = client.get(f"/api/cohorts/{job_id}/data?format=fhir")
    assert fhir.status_code == 200
    assert fhir.json()["resourceType"] == "Bundle"

    # OMOP
    omop = client.get(f"/api/cohorts/{job_id}/data?format=omop")
    assert omop.status_code == 200
    assert "person" in omop.json()

    # Data sheet PDF
    pdf = client.get(f"/api/cohorts/{job_id}/datasheet")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

    # Historial
    hist = client.get("/api/cohorts")
    assert hist.status_code == 200
    assert any(d["n_patients"] == 50 for d in hist.json())
