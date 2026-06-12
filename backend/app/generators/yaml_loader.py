"""
Carga única y cacheada del YAML de prevalencias clínicas.

El YAML reside en `backend/app/data/diabetes_t2_spain.yaml` y es la fuente
de verdad de todas las CPTs y distribuciones del generador. Cualquier
módulo que necesite valores epidemiológicos los lee desde aquí — nunca
hard-coded en otros archivos.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

_YAML_PATH = Path(__file__).resolve().parents[1] / "data" / "diabetes_t2_spain.yaml"


@functools.lru_cache(maxsize=1)
def load_prevalences() -> dict[str, Any]:
    """Carga el YAML una sola vez por proceso."""
    with _YAML_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
