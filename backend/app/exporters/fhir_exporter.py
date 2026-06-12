"""
FHIR R4 Bundle JSON.

Genera un Bundle `transaction` con recursos:
    Patient, Condition, MedicationStatement, Observation, Encounter.

Usamos `fhir.resources` para construir y validar cada recurso antes de
serializar. Si el paquete no está disponible (entorno sin fhir.resources
instalado) caemos a una representación tipo dict equivalente.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Iterable

from ..models.cohort import EncounterRecord, PatientRecord
from ..vocabularies import (
    CONDITIONS_ICD10, CONDITIONS_SNOMED, ICD10_SYSTEM, SNOMED_SYSTEM,
    DRUGS_ATC, ATC_SYSTEM,
    LABS_LOINC, LOINC_SYSTEM,
)

logger = logging.getLogger(__name__)


PATIENT_COMORBIDITIES = [
    ("hipertension", "hipertension"),
    ("dislipemia", "dislipemia"),
    ("nefropatia", "nefropatia"),
    ("retinopatia", "retinopatia"),
    ("neuropatia", "neuropatia"),
    ("cardiopatia", "cardiopatia"),
]

PATIENT_DRUGS = [
    "metformina", "insulina", "sulfonilureas",
    "idpp4", "isglt2", "arglp1", "pioglitazona",
]


def to_fhir_bundle(patients: Iterable[PatientRecord]) -> dict[str, Any]:
    """Construye un Bundle FHIR como dict serializable a JSON."""
    entries: list[dict] = []
    for p in patients:
        entries.extend(_patient_entries(p))
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries,
    }


# ──────────────────────────────────────────────────────────────────────
def _patient_entries(p: PatientRecord) -> list[dict]:
    entries: list[dict] = [_make_patient(p)]
    # Condition: diabetes T2 (siempre) + comorbilidades positivas
    entries.append(_make_condition(p, "diabetes_t2"))
    for attr, key in PATIENT_COMORBIDITIES:
        if getattr(p, attr):
            entries.append(_make_condition(p, key))
    # MedicationStatement por fármaco activo
    for drug in PATIENT_DRUGS:
        if getattr(p, drug):
            entries.append(_make_medication(p, drug))
    # Encuentros + observaciones
    for enc in p.encounters:
        entries.append(_make_encounter(p, enc))
        entries.extend(_make_observations(p, enc))
    return entries


def _make_patient(p: PatientRecord) -> dict:
    gender = "male" if p.sexo == "hombre" else "female"
    today = date.today()
    birth_year = today.year - p.edad
    birth_date = date(birth_year, 1, 1).isoformat()
    return {
        "fullUrl": f"urn:uuid:{p.patient_id}",
        "resource": {
            "resourceType": "Patient",
            "id": p.patient_id,
            "name": [{"family": p.apellidos, "given": [p.nombre]}],
            "gender": gender,
            "birthDate": birth_date,
            "address": [{"country": "ES", "state": p.region}],
        },
    }


def _make_condition(p: PatientRecord, key: str) -> dict:
    icd = CONDITIONS_ICD10[key]
    sno = CONDITIONS_SNOMED[key]
    return {
        "fullUrl": f"urn:uuid:cond-{p.patient_id}-{key}",
        "resource": {
            "resourceType": "Condition",
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }],
            },
            "code": {
                "coding": [
                    {"system": ICD10_SYSTEM, "code": icd["code"], "display": icd["display"]},
                    {"system": SNOMED_SYSTEM, "code": sno["code"], "display": sno["display"]},
                ],
            },
        },
    }


def _make_medication(p: PatientRecord, drug: str) -> dict:
    atc = DRUGS_ATC[drug]
    return {
        "fullUrl": f"urn:uuid:medstmt-{p.patient_id}-{drug}",
        "resource": {
            "resourceType": "MedicationStatement",
            "status": "active",
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "medicationCodeableConcept": {
                "coding": [
                    {"system": ATC_SYSTEM, "code": atc["code"], "display": atc["display"]},
                ],
            },
        },
    }


def _make_encounter(p: PatientRecord, enc: EncounterRecord) -> dict:
    return {
        "fullUrl": f"urn:uuid:{enc.encounter_id}",
        "resource": {
            "resourceType": "Encounter",
            "id": enc.encounter_id,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "ambulatory",
            },
            "subject": {"reference": f"Patient/{p.patient_id}"},
            "period": {
                "start": enc.encounter_date.isoformat(),
                "end": enc.encounter_date.isoformat(),
            },
        },
    }


def _make_observations(p: PatientRecord, enc: EncounterRecord) -> list[dict]:
    """Una Observation por biomarcador relevante."""
    measurements = [
        ("hba1c", enc.hba1c),
        ("glucemia_basal", enc.glucemia_basal),
        ("ldl", enc.ldl),
        ("hdl", enc.hdl),
        ("trigliceridos", enc.trigliceridos),
        ("presion_sistolica", enc.presion_sistolica),
        ("presion_diastolica", enc.presion_diastolica),
        ("filtrado_glomerular", enc.filtrado_glomerular),
        ("imc", enc.imc),
    ]
    obs = []
    for key, value in measurements:
        loinc = LABS_LOINC[key]
        obs.append({
            "fullUrl": f"urn:uuid:obs-{enc.encounter_id}-{key}",
            "resource": {
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "coding": [{
                        "system": LOINC_SYSTEM,
                        "code": loinc["code"],
                        "display": loinc["display"],
                    }],
                },
                "subject": {"reference": f"Patient/{p.patient_id}"},
                "encounter": {"reference": f"Encounter/{enc.encounter_id}"},
                "effectiveDateTime": enc.encounter_date.isoformat(),
                "valueQuantity": {
                    "value": float(value),
                    "unit": loinc["unit"],
                    "system": "http://unitsofmeasure.org",
                    "code": loinc["ucum"],
                },
            },
        })
    return obs
