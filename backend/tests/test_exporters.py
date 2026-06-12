"""Tests de validación estructural de los exportadores."""

from __future__ import annotations

import io
import csv as csv_module
import json

import pytest

from app.exporters import to_csv_string, to_fhir_bundle, to_omop_tables
from app.exporters.csv_exporter import CSV_COLUMNS
from app.exporters.omop_exporter import omop_tables_to_csv, OMOP_TABLES
from app.generators.pipeline import generate_cohort
from app.models.cohort import CohortConfig


@pytest.fixture(scope="module")
def patients():
    return generate_cohort(CohortConfig(n_patients=10, seed=3))


# ── CSV ───────────────────────────────────────────────────────────────
def test_csv_has_required_columns(patients):
    csv_str = to_csv_string(patients)
    reader = csv_module.DictReader(io.StringIO(csv_str))
    assert reader.fieldnames == CSV_COLUMNS
    rows = list(reader)
    # Una fila por encuentro
    expected_rows = sum(len(p.encounters) for p in patients)
    assert len(rows) == expected_rows
    for row in rows:
        assert row["patient_id"]
        assert row["encounter_id"]


# ── FHIR ──────────────────────────────────────────────────────────────
def test_fhir_bundle_structure(patients):
    bundle = to_fhir_bundle(patients)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    entries = bundle["entry"]
    assert len(entries) > 0

    types = {e["resource"]["resourceType"] for e in entries}
    assert "Patient" in types
    assert "Condition" in types        # al menos diabetes_t2
    assert "Observation" in types
    assert "Encounter" in types

    # serializable a JSON
    json.dumps(bundle)


def test_fhir_one_patient_resource_per_patient(patients):
    bundle = to_fhir_bundle(patients)
    patient_resources = [
        e for e in bundle["entry"]
        if e["resource"]["resourceType"] == "Patient"
    ]
    assert len(patient_resources) == len(patients)


def test_fhir_observation_has_loinc_code(patients):
    bundle = to_fhir_bundle(patients)
    for entry in bundle["entry"]:
        res = entry["resource"]
        if res["resourceType"] != "Observation":
            continue
        codings = res["code"]["coding"]
        assert any(c["system"] == "http://loinc.org" for c in codings)
        assert "valueQuantity" in res


# ── OMOP ──────────────────────────────────────────────────────────────
def test_omop_has_all_tables(patients):
    tables = to_omop_tables(patients)
    assert set(tables.keys()) == set(OMOP_TABLES)
    assert len(tables["person"]) == len(patients)
    assert len(tables["condition_occurrence"]) >= len(patients)   # al menos DM2
    assert len(tables["visit_occurrence"]) == sum(len(p.encounters) for p in patients)


def test_omop_csv_serialization(patients):
    tables = to_omop_tables(patients)
    csvs = omop_tables_to_csv(tables)
    for name in OMOP_TABLES:
        # person, condition_occurrence, visit_occurrence, measurement no estarán vacías
        if name in ("person", "visit_occurrence", "measurement", "condition_occurrence"):
            assert csvs[name].strip(), f"Tabla {name} vacía"


def test_omop_person_ids_unique(patients):
    tables = to_omop_tables(patients)
    ids = [row["person_id"] for row in tables["person"]]
    assert len(ids) == len(set(ids))
