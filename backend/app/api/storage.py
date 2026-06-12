"""
Persistencia simple en SQLite — pensado para MVP. La estructura es
preparada para migrar a PostgreSQL cambiando la URL del engine.

Tablas:
    jobs       — estado del proceso de generación (queued/running/done/failed)
    datasets   — payload completo de la cohorte (JSON blob)
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Float, JSON, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    progress = Column(Float, default=0.0)
    message = Column(Text, default="")
    dataset_id = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id = Column(String, primary_key=True)
    created_at = Column(DateTime, nullable=False)
    config_json = Column(JSON, nullable=False)
    patients_json = Column(JSON, nullable=False)
    metrics_json = Column(JSON, nullable=True)


def _get_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./synthehds.db")
    return create_engine(url, future=True, connect_args=(
        {"check_same_thread": False} if url.startswith("sqlite") else {}
    ))


_engine = _get_engine()
SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def now() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────
# Jobs
# ──────────────────────────────────────────────────────────────────────
def create_job() -> str:
    job_id = str(uuid.uuid4())
    with SessionLocal() as s:
        s.add(Job(
            job_id=job_id, status="queued", progress=0.0, message="",
            created_at=now(), updated_at=now(),
        ))
        s.commit()
    return job_id


def update_job(
    job_id: str, *,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    message: Optional[str] = None,
    dataset_id: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job:
            return
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if dataset_id is not None:
            job.dataset_id = dataset_id
        if error is not None:
            job.error = error
        job.updated_at = now()
        s.commit()


def get_job(job_id: str) -> Optional[dict]:
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if not j:
            return None
        return _job_to_dict(j)


def _job_to_dict(j: Job) -> dict:
    return {
        "job_id": j.job_id, "status": j.status, "progress": j.progress,
        "message": j.message or "", "dataset_id": j.dataset_id,
        "error": j.error, "created_at": j.created_at, "updated_at": j.updated_at,
    }


# ──────────────────────────────────────────────────────────────────────
# Datasets
# ──────────────────────────────────────────────────────────────────────
def save_dataset(
    dataset_id: str, config_json: dict, patients_json: list, metrics_json: dict | None,
) -> None:
    with SessionLocal() as s:
        s.add(Dataset(
            dataset_id=dataset_id,
            created_at=now(),
            config_json=config_json,
            patients_json=patients_json,
            metrics_json=metrics_json,
        ))
        s.commit()


def get_dataset(dataset_id: str) -> Optional[dict]:
    with SessionLocal() as s:
        d = s.get(Dataset, dataset_id)
        if not d:
            return None
        return {
            "dataset_id": d.dataset_id,
            "created_at": d.created_at,
            "config": d.config_json,
            "patients": d.patients_json,
            "metrics": d.metrics_json,
        }


def list_datasets(limit: int = 50, offset: int = 0) -> list[dict]:
    with SessionLocal() as s:
        results = (
            s.query(Dataset)
            .order_by(Dataset.created_at.desc())
            .offset(offset).limit(limit).all()
        )
        return [{
            "dataset_id": d.dataset_id,
            "created_at": d.created_at,
            "n_patients": len(d.patients_json) if d.patients_json else 0,
            "config": d.config_json,
        } for d in results]
