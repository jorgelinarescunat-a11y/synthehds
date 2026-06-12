"""Test end-to-end del pipeline de generación."""

from __future__ import annotations

import pytest

from app.generators.pipeline import generate_cohort
from app.models.cohort import CohortConfig


@pytest.fixture(scope="module")
def cohort_patients():
    cfg = CohortConfig(n_patients=50, seed=7)
    return generate_cohort(cfg)


def test_cohort_size(cohort_patients):
    assert len(cohort_patients) == 50


def test_patients_have_ids_and_encounters(cohort_patients):
    for p in cohort_patients:
        assert p.patient_id and len(p.patient_id) == 36   # UUID v4
        assert 3 <= len(p.encounters) <= 5
        # encuentros ordenados por número
        nums = [e.encounter_number for e in p.encounters]
        assert nums == sorted(nums)


def test_no_real_identifiers(cohort_patients):
    """No deben aparecer DNIs ni patrones identificables — faker locale es_ES."""
    import re
    dni_pattern = re.compile(r"\b\d{8}[A-Z]\b")
    for p in cohort_patients:
        for field in (p.nombre, p.apellidos, p.patient_id):
            assert not dni_pattern.search(field)


def test_filters_exclude_comorbidity():
    cfg = CohortConfig(
        n_patients=30, seed=11, excluir_comorbilidades=["hipertension"]
    )
    patients = generate_cohort(cfg)
    assert all(not p.hipertension for p in patients)


def test_filters_force_comorbidity():
    cfg = CohortConfig(
        n_patients=20, seed=13, forzar_comorbilidades=["nefropatia"]
    )
    patients = generate_cohort(cfg)
    assert all(p.nefropatia for p in patients)


def test_age_range():
    cfg = CohortConfig(n_patients=30, edad_min=50, edad_max=70, seed=17)
    patients = generate_cohort(cfg)
    for p in patients:
        assert 50 <= p.edad <= 70
