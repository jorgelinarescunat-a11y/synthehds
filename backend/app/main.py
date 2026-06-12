"""
SynthEHDS — FastAPI application entry point.

Monta el router de cohortes y crea las tablas SQLite al arrancar.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .api import storage
from .api.cohorts import router as cohorts_router

APP_NAME = "SynthEHDS"
APP_VERSION = "0.1.0"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Generador de datasets sintéticos de pacientes con diabetes tipo 2 "
        "en España, alineado con los principios del European Health Data Space."
    ),
)

_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    storage.init_db()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    environment: str


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=APP_NAME,
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=os.getenv("ENVIRONMENT", "development"),
    )


app.include_router(cohorts_router)
