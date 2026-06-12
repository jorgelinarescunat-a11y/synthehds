"""
Generación opcional de notas clínicas tipo SOAP en español médico,
usando la API de Anthropic Claude.

El LLM **no genera ningún dato estadístico**: solo prosa que parafrasea
los datos estructurados ya producidos por la BN. Si la API falla o no
hay clave configurada, los encuentros quedan sin nota y el resto del
pipeline continúa.

Caché en memoria por hash de inputs — evita regenerar notas idénticas
en una misma sesión.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import Optional

from ..models.cohort import EncounterRecord, PatientRecord

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5"
_MAX_TOKENS = 400


SYSTEM_PROMPT = """Eres un médico de familia español redactando una nota \
clínica tipo SOAP (Subjetivo, Objetivo, Análisis, Plan) en español médico \
formal pero conciso. Te dan datos estructurados de un paciente con \
diabetes tipo 2 y debes escribir una nota de 80-150 palabras. No inventes \
datos no proporcionados. No incluyas información identificable ficticia \
(DNIs, teléfonos, direcciones reales). Usa terminología SNS habitual."""


def _payload_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _build_payload(patient: PatientRecord, enc: EncounterRecord) -> dict:
    return {
        "edad": patient.edad,
        "sexo": patient.sexo,
        "años_evolucion": patient.años_evolucion,
        "imc": enc.imc,
        "hba1c": enc.hba1c,
        "glucemia_basal": enc.glucemia_basal,
        "presion_sistolica": enc.presion_sistolica,
        "presion_diastolica": enc.presion_diastolica,
        "ldl": enc.ldl,
        "hdl": enc.hdl,
        "filtrado_glomerular": enc.filtrado_glomerular,
        "comorbilidades": [
            c for c, v in {
                "hipertensión": patient.hipertension,
                "dislipemia": patient.dislipemia,
                "nefropatía": patient.nefropatia,
                "retinopatía": patient.retinopatia,
                "neuropatía": patient.neuropatia,
                "cardiopatía isquémica": patient.cardiopatia,
            }.items() if v
        ],
        "tratamiento_actual": [
            d for d, v in {
                "metformina": patient.metformina,
                "insulina": patient.insulina,
                "sulfonilureas": patient.sulfonilureas,
                "iDPP4": patient.idpp4,
                "iSGLT2": patient.isglt2,
                "arGLP1": patient.arglp1,
                "pioglitazona": patient.pioglitazona,
            }.items() if v
        ],
        "numero_visita": enc.encounter_number,
    }


_NOTE_CACHE: dict[str, str] = {}


def generate_note(
    patient: PatientRecord,
    enc: EncounterRecord,
    *,
    api_key: Optional[str] = None,
    model: str = _DEFAULT_MODEL,
) -> Optional[str]:
    """
    Devuelve una nota SOAP o None si la API no está disponible.
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    payload = _build_payload(patient, enc)
    cache_key = _payload_hash(payload)
    if cache_key in _NOTE_CACHE:
        return _NOTE_CACHE[cache_key]

    try:
        import anthropic
    except ImportError:
        logger.warning("Paquete `anthropic` no instalado — nota omitida.")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Redacta la nota SOAP en español, 80-150 palabras, "
        "estructura S/O/A/P explícita.\n\n"
        f"Datos del paciente:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "text", None)
        ).strip()
    except Exception as exc:
        logger.warning("Anthropic API falló: %s — encuentro sin nota.", exc)
        return None

    _NOTE_CACHE[cache_key] = text
    return text


def attach_notes_to_cohort(
    patients: list[PatientRecord],
    *,
    api_key: Optional[str] = None,
    model: str = _DEFAULT_MODEL,
) -> None:
    """Recorre la cohorte y rellena `nota_clinica` en cada encuentro.
    Modifica los pacientes in-place. Errores individuales no detienen
    el resto."""
    if not (api_key or os.getenv("ANTHROPIC_API_KEY")):
        logger.info("ANTHROPIC_API_KEY no configurada — sin notas.")
        return
    for p in patients:
        for enc in p.encounters:
            enc.nota_clinica = generate_note(p, enc, api_key=api_key, model=model)
