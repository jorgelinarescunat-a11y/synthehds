"""Tests del módulo de métricas de calidad."""

from __future__ import annotations

import pytest

from app.generators.pipeline import generate_cohort
from app.models.cohort import CohortConfig
from app.quality import compute_quality_metrics


@pytest.fixture(scope="module")
def metrics():
    patients = generate_cohort(CohortConfig(n_patients=100, seed=99))
    return compute_quality_metrics(patients)


def test_fidelity_has_categorical_and_continuous(metrics):
    fid = metrics.fidelidad_estadistica
    assert "categoricas" in fid and "continuas" in fid
    assert "hipertension" in fid["categoricas"]
    assert "ldl" in fid["continuas"]


def test_correlations_directionally_correct(metrics):
    corr = metrics.correlaciones
    # Esperamos OR observado > 1 en pares con OR esperado > 1
    for key, vals in corr.items():
        if vals["or_observado"] is None:
            continue
        if vals["or_esperado"] > 1:
            # No exigimos magnitud exacta, sólo dirección
            assert vals["or_observado"] >= 1.0, (
                f"{key}: OR observado {vals['or_observado']} "
                f"vs esperado {vals['or_esperado']}"
            )


def test_privacy_uniqueness_keys(metrics):
    priv = metrics.privacidad_unicidad
    assert "n_pacientes" in priv
    assert "pct_unicas" in priv
    assert 0 <= priv["pct_unicas"] <= 100


def test_coherence_score_is_high(metrics):
    coh = metrics.coherencia_clinica
    assert coh["hba1c_minimo_5_5"] is True
    assert coh["edad_diag_adulto"] is True
    assert coh["edad_diag_no_supera_edad"] is True
    assert coh["score_global_pct"] >= 95.0
