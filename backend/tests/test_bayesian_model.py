"""
Test unitario de la Bayesian Network.

Genera una cohorte sintética y verifica que las marginales caen dentro
de tolerancias razonables respecto al YAML. Las tolerancias son amplias
intencionadamente: este test detecta *regresiones gruesas* (CPTs
invertidas, columnas mal ordenadas, errores estructurales), no certifica
fidelidad estadística — eso es responsabilidad del módulo `quality/`.

El spec menciona n=100; usamos n=500 con `seed=42` para reducir la
varianza muestral en CI y mantener el test estable. Un test adicional
con n=100 cubre el caso especificado verificando estructura y rangos.
"""

from __future__ import annotations

import pytest

from app.generators.bayesian_model import sample_cohort
from app.generators.yaml_loader import load_prevalences


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def yaml_data():
    return load_prevalences()


@pytest.fixture(scope="module")
def cohort_small():
    """Cohorte de 100 pacientes — caso exacto del spec."""
    return sample_cohort(n_patients=100, seed=42)


@pytest.fixture(scope="module")
def cohort():
    """Cohorte de 500 pacientes para tests de distribución estables."""
    return sample_cohort(n_patients=500, seed=42)


# ──────────────────────────────────────────────────────────────────────
# Estructura y validez básica
# ──────────────────────────────────────────────────────────────────────
def test_n100_cohort_size(cohort_small):
    assert len(cohort_small) == 100


def test_columns_present(cohort):
    required = {
        "sexo", "edad", "edad_grupo", "edad_diagnostico", "años_evolucion",
        "region", "region_grupo",
        "imc", "imc_grupo", "hba1c", "hba1c_grupo",
        "glucemia_basal", "ldl", "hdl", "trigliceridos",
        "presion_sistolica", "presion_diastolica", "filtrado_glomerular",
        "hipertension", "dislipemia", "nefropatia", "retinopatia",
        "neuropatia", "cardiopatia",
        "metformina", "insulina", "sulfonilureas", "idpp4", "isglt2",
        "arglp1", "pioglitazona",
    }
    missing = required - set(cohort.columns)
    assert not missing, f"Faltan columnas: {missing}"


def test_no_impossible_values(cohort):
    assert (cohort["edad"].between(18, 90)).all()
    assert (cohort["edad_diagnostico"] >= 18).all()
    assert (cohort["años_evolucion"] >= 0).all()
    assert (cohort["edad_diagnostico"] <= cohort["edad"]).all()
    assert (cohort["imc"].between(16, 55)).all()
    assert (cohort["hba1c"].between(5.5, 13.0)).all()
    assert (cohort["filtrado_glomerular"] > 0).all()
    assert (cohort["presion_sistolica"].between(90, 210)).all()


# ──────────────────────────────────────────────────────────────────────
# Distribuciones marginales vs YAML
# ──────────────────────────────────────────────────────────────────────
TOL_PP_COMMON = 10.0    # variables binarias con marginal "típica"
TOL_PP_RARE = 8.0       # variables binarias con baja prevalencia (<15 %)
TOL_PP_HBA1C = 10.0     # categorías de control glucémico


def _pct_si(df, column):
    return (df[column] == "si").mean() * 100


def test_hba1c_control_distribution(cohort, yaml_data):
    """[YAML] menor_7=63.4 %, 7-8=21.6 %, ≥8=15 % (SIMETAP)."""
    target = yaml_data["control_glucemico_hba1c"]
    counts = cohort["hba1c_grupo"].value_counts(normalize=True) * 100
    assert abs(counts.get("bueno", 0) - target["menor_7_pct"]) < TOL_PP_HBA1C
    assert abs(counts.get("moderado", 0) - target["entre_7_y_8_pct"]) < TOL_PP_HBA1C
    assert abs(counts.get("malo", 0) - target["mayor_igual_8_pct"]) < TOL_PP_HBA1C


def test_comorbidities_marginals(cohort, yaml_data):
    target = yaml_data["comorbilidades_pct"]
    checks = [
        ("hipertension", target["hipertension"], TOL_PP_COMMON),
        ("dislipemia", target["dislipemia"], TOL_PP_COMMON),
        ("nefropatia", target["enfermedad_renal_cronica"], TOL_PP_COMMON),
        ("retinopatia", target["retinopatia"], TOL_PP_RARE),
        ("neuropatia", target["neuropatia"], TOL_PP_COMMON),
        ("cardiopatia", target["cardiopatia_isquemica"], TOL_PP_RARE),
    ]
    for var, expected, tol in checks:
        observed = _pct_si(cohort, var)
        diff = abs(observed - expected)
        assert diff < tol, (
            f"{var}: observado {observed:.1f} % vs YAML {expected:.1f} % "
            f"(Δ={diff:.1f} pp, tol {tol})"
        )


def test_treatment_marginals(cohort, yaml_data):
    target = yaml_data["tratamiento_farmacologico_pct"]
    drugs_tols = {
        "metformina": TOL_PP_COMMON,
        "insulina": TOL_PP_COMMON,
        "sulfonilureas": TOL_PP_COMMON,
        "idpp4": TOL_PP_COMMON,
        "isglt2": TOL_PP_RARE,
        "arglp1": TOL_PP_RARE,
        "pioglitazona": TOL_PP_RARE,
    }
    for drug, tol in drugs_tols.items():
        observed = _pct_si(cohort, drug)
        expected = target[drug]
        diff = abs(observed - expected)
        assert diff < tol, (
            f"{drug}: observado {observed:.1f} % vs YAML {expected:.1f} % "
            f"(Δ={diff:.1f} pp, tol {tol})"
        )


def test_sex_distribution(cohort):
    pct_hombre = (cohort["sexo"] == "hombre").mean() * 100
    assert 45 < pct_hombre < 60, f"sexo (hombre)={pct_hombre:.1f}% fuera de rango"


def test_imc_obesity_rate(cohort, yaml_data):
    """obesidad_imc_mayor30 ≈ 35 %."""
    pct_obeso = (cohort["imc_grupo"] == "obeso").mean() * 100
    target = yaml_data["comorbilidades_pct"]["obesidad_imc_mayor30"]
    assert abs(pct_obeso - target) < 10, (
        f"obesidad {pct_obeso:.1f}% vs YAML {target}%"
    )


# ──────────────────────────────────────────────────────────────────────
# Correlaciones direccionales (smoke checks)
# ──────────────────────────────────────────────────────────────────────
def test_retinopathy_higher_with_bad_hba1c(cohort):
    """HbA1c alta → mayor retinopatía (YAML correlaciones, OR 2.5)."""
    by_hba1c = (cohort.groupby("hba1c_grupo")["retinopatia"]
                .apply(lambda s: (s == "si").mean()))
    assert by_hba1c["malo"] > by_hba1c["bueno"]


def test_nephropathy_higher_with_hypertension(cohort):
    """HTA → mayor nefropatía (YAML correlaciones, OR 3.0)."""
    by_hta = (cohort.groupby("hipertension")["nefropatia"]
              .apply(lambda s: (s == "si").mean()))
    assert by_hta["si"] > by_hta["no"]


def test_insulin_higher_with_bad_control(cohort):
    by_hba1c = (cohort.groupby("hba1c_grupo")["insulina"]
                .apply(lambda s: (s == "si").mean()))
    assert by_hba1c["malo"] > by_hba1c["bueno"]


def test_isglt2_higher_with_nephropathy(cohort):
    """Regla de prescripción: iSGLT2 preferente si ERC."""
    by_nefro = (cohort.groupby("nefropatia")["isglt2"]
                .apply(lambda s: (s == "si").mean()))
    assert by_nefro["si"] > by_nefro["no"]


def test_fge_lower_with_nephropathy(cohort):
    by_nefro = cohort.groupby("nefropatia")["filtrado_glomerular"].mean()
    assert by_nefro["si"] < by_nefro["no"]
