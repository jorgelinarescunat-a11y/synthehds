"""
Endpoints /api/cohorts/* — generación asíncrona y consulta.

Estados de un job: queued → running → done / failed.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from ..exporters import to_csv_string, to_fhir_bundle, to_omop_tables
from ..exporters.datasheet import build_datasheet
from ..exporters.omop_exporter import omop_tables_to_csv
from ..generators.pipeline import generate_cohort
from ..models.cohort import (
    CohortConfig, CohortJobStatus, PatientRecord, QualityMetrics,
)
from ..narratives import attach_notes_to_cohort
from ..quality import compute_quality_metrics
from . import storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])


# ──────────────────────────────────────────────────────────────────────
# Generación asíncrona
# ──────────────────────────────────────────────────────────────────────
@router.post("/generate")
def generate(config: CohortConfig, bg: BackgroundTasks):
    job_id = storage.create_job()
    bg.add_task(_run_job, job_id, config)
    return {"job_id": job_id, "status": "queued"}


def _run_job(job_id: str, config: CohortConfig) -> None:
    try:
        storage.update_job(job_id, status="running", progress=0.1,
                           message="Generando cohorte…")
        patients = generate_cohort(config)
        storage.update_job(job_id, progress=0.55, message="Calculando métricas…")
        metrics = compute_quality_metrics(patients)

        if config.generar_notas_clinicas:
            storage.update_job(job_id, progress=0.75,
                               message="Generando notas clínicas con Claude…")
            attach_notes_to_cohort(patients)

        dataset_id = str(uuid.uuid4())
        storage.save_dataset(
            dataset_id=dataset_id,
            config_json=json.loads(config.model_dump_json()),
            patients_json=[json.loads(p.model_dump_json()) for p in patients],
            metrics_json=json.loads(metrics.model_dump_json()),
        )
        storage.update_job(
            job_id, status="done", progress=1.0,
            message=f"{len(patients)} pacientes generados.",
            dataset_id=dataset_id,
        )
    except Exception as exc:
        logger.exception("Job %s falló: %s", job_id, exc)
        storage.update_job(job_id, status="failed", error=str(exc))


# ──────────────────────────────────────────────────────────────────────
# Consulta de estado
# ──────────────────────────────────────────────────────────────────────
@router.get("/{job_id}/status", response_model=CohortJobStatus)
def status(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    return CohortJobStatus(**job)


# ──────────────────────────────────────────────────────────────────────
# Descarga de datos según formato
# ──────────────────────────────────────────────────────────────────────
def _patients_from_dataset(dataset_id: str) -> tuple[list[PatientRecord], dict, QualityMetrics | None]:
    ds = storage.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset no encontrado")
    patients = [PatientRecord(**p) for p in ds["patients"]]
    metrics = QualityMetrics(**ds["metrics"]) if ds["metrics"] else None
    return patients, ds["config"], metrics


def _resolve_dataset_id(job_id: str) -> str:
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    if job["status"] != "done" or not job["dataset_id"]:
        raise HTTPException(409, f"Job en estado {job['status']}")
    return job["dataset_id"]


@router.get("/{job_id}/data")
def download(job_id: str, format: str = Query("csv", regex="^(csv|fhir|omop)$")):
    dataset_id = _resolve_dataset_id(job_id)
    patients, _config, _metrics = _patients_from_dataset(dataset_id)

    if format == "csv":
        return PlainTextResponse(
            to_csv_string(patients),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cohort_{job_id}.csv"'},
        )
    if format == "fhir":
        return JSONResponse(to_fhir_bundle(patients))
    if format == "omop":
        tables = omop_tables_to_csv(to_omop_tables(patients))
        return JSONResponse(tables)
    raise HTTPException(400, "Formato no soportado")


@router.get("/{job_id}/metrics")
def metrics(job_id: str):
    dataset_id = _resolve_dataset_id(job_id)
    _patients, _config, mets = _patients_from_dataset(dataset_id)
    if not mets:
        raise HTTPException(404, "Sin métricas disponibles")
    return JSONResponse(json.loads(mets.model_dump_json()))


@router.get("/{job_id}/preview")
def preview(job_id: str, limit: int = 20):
    dataset_id = _resolve_dataset_id(job_id)
    patients, config, _metrics = _patients_from_dataset(dataset_id)
    rows = []
    for p in patients[:limit]:
        rows.append(json.loads(p.model_dump_json(exclude={"encounters"})))
    return {
        "dataset_id": dataset_id,
        "n_total": len(patients),
        "config": config,
        "preview": rows,
    }


@router.get("/{job_id}/datasheet")
def datasheet(job_id: str):
    dataset_id = _resolve_dataset_id(job_id)
    patients, config_dict, mets = _patients_from_dataset(dataset_id)
    if mets is None:
        raise HTTPException(409, "Faltan métricas para generar el data sheet")
    config = CohortConfig(**config_dict)
    pdf_bytes = build_datasheet(
        dataset_id=dataset_id,
        config=config,
        metrics=mets,
        n_patients=len(patients),
        n_encounters=sum(len(p.encounters) for p in patients),
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="datasheet_{job_id}.pdf"'},
    )


# ──────────────────────────────────────────────────────────────────────
# Historial
# ──────────────────────────────────────────────────────────────────────
@router.get("")
def history(limit: int = 50, offset: int = 0):
    return storage.list_datasets(limit=limit, offset=offset)
