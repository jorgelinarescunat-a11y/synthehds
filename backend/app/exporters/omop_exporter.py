"""
OMOP Common Data Model v5.4 — exportación a 5 tablas mínimas:
  person, condition_occurrence, drug_exposure, measurement, visit_occurrence.

Devuelve un dict {nombre_tabla: lista_de_filas} listo para serializar a
CSV. Como no manejamos vocabularios OMOP completos (concept_id numérico
requiere ATHENA), llenamos los campos `*_source_value` con los códigos
ICD-10 / ATC / LOINC y dejamos los `*_concept_id` en 0 — práctica
habitual en pipelines OMOP que harán el mapeo OHDSI a posteriori.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from ..models.cohort import EncounterRecord, PatientRecord
from ..vocabularies import (
    CONDITIONS_ICD10, DRUGS_ATC, LABS_LOINC,
)

OMOP_TABLES = [
    "person", "condition_occurrence", "drug_exposure",
    "measurement", "visit_occurrence",
]


def to_omop_tables(patients: Iterable[PatientRecord]) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {t: [] for t in OMOP_TABLES}

    person_id_seq = 0
    visit_id_seq = 0
    cond_id_seq = 0
    drug_id_seq = 0
    meas_id_seq = 0

    today = date.today()
    for p in patients:
        person_id_seq += 1
        person_id = person_id_seq
        # ── person
        gender_concept = 8507 if p.sexo == "hombre" else 8532   # OMOP std
        birth_year = today.year - p.edad
        tables["person"].append({
            "person_id": person_id,
            "gender_concept_id": gender_concept,
            "year_of_birth": birth_year,
            "race_concept_id": 0,
            "ethnicity_concept_id": 0,
            "gender_source_value": p.sexo,
            "person_source_value": p.patient_id,
            "location_source_value": p.region,
        })

        # ── condition_occurrence: DM2 + comorbilidades positivas
        condition_keys = ["diabetes_t2"]
        for attr, key in [
            ("hipertension", "hipertension"), ("dislipemia", "dislipemia"),
            ("nefropatia", "nefropatia"), ("retinopatia", "retinopatia"),
            ("neuropatia", "neuropatia"), ("cardiopatia", "cardiopatia"),
        ]:
            if getattr(p, attr):
                condition_keys.append(key)
        dx_date = date(today.year - p.años_evolucion, 6, 15).isoformat()
        for ck in condition_keys:
            cond_id_seq += 1
            icd = CONDITIONS_ICD10[ck]
            tables["condition_occurrence"].append({
                "condition_occurrence_id": cond_id_seq,
                "person_id": person_id,
                "condition_concept_id": 0,
                "condition_start_date": dx_date,
                "condition_type_concept_id": 32020,   # EHR
                "condition_source_value": icd["code"],
                "condition_source_concept_id": 0,
            })

        # ── drug_exposure por fármaco activo (start = fecha primer encuentro)
        first_enc_date = p.encounters[0].encounter_date.date().isoformat() \
            if p.encounters else dx_date
        for drug in [
            "metformina", "insulina", "sulfonilureas",
            "idpp4", "isglt2", "arglp1", "pioglitazona",
        ]:
            if not getattr(p, drug):
                continue
            drug_id_seq += 1
            atc = DRUGS_ATC[drug]
            tables["drug_exposure"].append({
                "drug_exposure_id": drug_id_seq,
                "person_id": person_id,
                "drug_concept_id": 0,
                "drug_exposure_start_date": first_enc_date,
                "drug_type_concept_id": 38000177,   # prescription written
                "drug_source_value": atc["code"],
            })

        # ── visit_occurrence + measurement por encuentro
        for enc in p.encounters:
            visit_id_seq += 1
            visit_id = visit_id_seq
            tables["visit_occurrence"].append({
                "visit_occurrence_id": visit_id,
                "person_id": person_id,
                "visit_concept_id": 9202,           # outpatient
                "visit_start_date": enc.encounter_date.date().isoformat(),
                "visit_end_date": enc.encounter_date.date().isoformat(),
                "visit_type_concept_id": 32020,
            })
            for biomarker, value in [
                ("hba1c", enc.hba1c),
                ("glucemia_basal", enc.glucemia_basal),
                ("ldl", enc.ldl),
                ("hdl", enc.hdl),
                ("trigliceridos", enc.trigliceridos),
                ("presion_sistolica", enc.presion_sistolica),
                ("presion_diastolica", enc.presion_diastolica),
                ("filtrado_glomerular", enc.filtrado_glomerular),
                ("imc", enc.imc),
            ]:
                meas_id_seq += 1
                loinc = LABS_LOINC[biomarker]
                tables["measurement"].append({
                    "measurement_id": meas_id_seq,
                    "person_id": person_id,
                    "measurement_concept_id": 0,
                    "measurement_date": enc.encounter_date.date().isoformat(),
                    "visit_occurrence_id": visit_id,
                    "value_as_number": float(value),
                    "unit_source_value": loinc["unit"],
                    "measurement_source_value": loinc["code"],
                    "measurement_type_concept_id": 32817,   # EHR
                })

    return tables


def omop_tables_to_csv(tables: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    """Serializa cada tabla OMOP a un CSV string."""
    import csv
    import io

    result: dict[str, str] = {}
    for name, rows in tables.items():
        if not rows:
            result[name] = ""
            continue
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        result[name] = buf.getvalue()
    return result
