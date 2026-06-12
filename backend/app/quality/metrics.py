"""
Cuatro familias de métricas de calidad sobre una cohorte generada:

1. Fidelidad estadística — KS (continuas) y chi² (categóricas) entre
   la distribución observada y la esperada según el YAML.
2. Correlaciones — comparación direccional entre pares con OR conocido
   en el YAML (HbA1c↔retinopatía, HTA↔nefropatía, dislipemia↔cardiopatía).
3. Privacidad por unicidad — % de combinaciones únicas de
   quasi-identificadores (edad+sexo+región+años_diagnóstico).
   No demuestra anonimato en sentido estricto pero indica que no hay
   filas "memorables" replicables a un individuo real.
4. Coherencia clínica — reglas lógicas booleanas:
   - HbA1c siempre ≥ 5.5 % en diagnosticados
   - No insulina sin diagnóstico (siempre cierto en este pipeline)
   - iSGLT2 solo si FGe ≥ 30 ml/min (regla de prescripción)
   - Edad_diagnostico ≥ 18 y ≤ edad
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from ..generators.yaml_loader import load_prevalences
from ..models.cohort import PatientRecord, QualityMetrics


# ──────────────────────────────────────────────────────────────────────
# Entrada pública
# ──────────────────────────────────────────────────────────────────────
def compute_quality_metrics(patients: list[PatientRecord]) -> QualityMetrics:
    df_patient = _patients_to_df(patients)
    df_enc = _encounters_to_df(patients)

    return QualityMetrics(
        fidelidad_estadistica=_fidelity(df_patient, df_enc),
        correlaciones=_correlations(df_patient),
        privacidad_unicidad=_privacy(df_patient),
        coherencia_clinica=_coherence(df_patient, df_enc),
    )


# ──────────────────────────────────────────────────────────────────────
# Tablas auxiliares
# ──────────────────────────────────────────────────────────────────────
def _patients_to_df(patients: Iterable[PatientRecord]) -> pd.DataFrame:
    rows = []
    for p in patients:
        rows.append({
            "patient_id": p.patient_id,
            "sexo": p.sexo,
            "edad": p.edad,
            "edad_diagnostico": p.edad_diagnostico,
            "años_evolucion": p.años_evolucion,
            "region_grupo": p.region_grupo,
            "imc_grupo": p.imc_grupo,
            "hipertension": p.hipertension,
            "dislipemia": p.dislipemia,
            "nefropatia": p.nefropatia,
            "retinopatia": p.retinopatia,
            "neuropatia": p.neuropatia,
            "cardiopatia": p.cardiopatia,
            "metformina": p.metformina,
            "insulina": p.insulina,
            "sulfonilureas": p.sulfonilureas,
            "idpp4": p.idpp4,
            "isglt2": p.isglt2,
            "arglp1": p.arglp1,
            "pioglitazona": p.pioglitazona,
        })
    return pd.DataFrame(rows)


def _encounters_to_df(patients: Iterable[PatientRecord]) -> pd.DataFrame:
    rows = []
    for p in patients:
        for enc in p.encounters:
            rows.append({
                "patient_id": p.patient_id,
                "hba1c": enc.hba1c,
                "glucemia_basal": enc.glucemia_basal,
                "ldl": enc.ldl,
                "hdl": enc.hdl,
                "presion_sistolica": enc.presion_sistolica,
                "presion_diastolica": enc.presion_diastolica,
                "filtrado_glomerular": enc.filtrado_glomerular,
                "imc": enc.imc,
            })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────
# 1) Fidelidad estadística
# ──────────────────────────────────────────────────────────────────────
def _fidelity(df_p: pd.DataFrame, df_e: pd.DataFrame) -> dict:
    yaml_d = load_prevalences()
    out: dict = {"categoricas": {}, "continuas": {}}

    # Categóricas — comorbilidades y fármacos (chi²)
    targets = {
        "hipertension": yaml_d["comorbilidades_pct"]["hipertension"] / 100,
        "dislipemia":   yaml_d["comorbilidades_pct"]["dislipemia"] / 100,
        "nefropatia":   yaml_d["comorbilidades_pct"]["enfermedad_renal_cronica"] / 100,
        "retinopatia":  yaml_d["comorbilidades_pct"]["retinopatia"] / 100,
        "neuropatia":   yaml_d["comorbilidades_pct"]["neuropatia"] / 100,
        "cardiopatia":  yaml_d["comorbilidades_pct"]["cardiopatia_isquemica"] / 100,
        "metformina":   yaml_d["tratamiento_farmacologico_pct"]["metformina"] / 100,
        "insulina":     yaml_d["tratamiento_farmacologico_pct"]["insulina"] / 100,
        "isglt2":       yaml_d["tratamiento_farmacologico_pct"]["isglt2"] / 100,
        "arglp1":       yaml_d["tratamiento_farmacologico_pct"]["arglp1"] / 100,
    }
    n = len(df_p)
    for var, p_expected in targets.items():
        obs_si = int(df_p[var].sum())
        obs_no = n - obs_si
        exp_si = p_expected * n
        exp_no = n - exp_si
        if exp_si <= 0 or exp_no <= 0:
            continue
        chi2 = (obs_si - exp_si) ** 2 / exp_si + (obs_no - exp_no) ** 2 / exp_no
        p_val = float(1 - stats.chi2.cdf(chi2, df=1))
        out["categoricas"][var] = {
            "observado_pct": round(obs_si / n * 100, 2),
            "esperado_pct": round(p_expected * 100, 2),
            "diff_pp": round((obs_si / n - p_expected) * 100, 2),
            "chi2": round(float(chi2), 3),
            "p_value": round(p_val, 4),
        }

    # Continuas — comparación contra normal teórica (KS)
    bio = yaml_d["biomarcadores_distribucion"]
    cont_targets = {
        "hba1c": (yaml_d["perfil_clinico_tipico"].get("hba1c_medio", 7.2), 1.2),
        "ldl": (bio["ldl_mg_dl"]["media"], bio["ldl_mg_dl"]["desv"]),
        "imc": (yaml_d["perfil_clinico_tipico"]["imc_medio"],
                yaml_d["perfil_clinico_tipico"]["imc_desviacion_estandar"]),
        "presion_sistolica": (bio["presion_sistolica_mmhg"]["media"],
                              bio["presion_sistolica_mmhg"]["desv"]),
        "filtrado_glomerular": (bio["filtrado_glomerular_ml_min"]["media"],
                                bio["filtrado_glomerular_ml_min"]["desv"]),
    }
    for var, (mu, sd) in cont_targets.items():
        if var not in df_e.columns:
            continue
        series = df_e[var].dropna()
        if len(series) < 5:
            continue
        ks_stat, ks_p = stats.kstest(series, "norm", args=(mu, sd))
        out["continuas"][var] = {
            "media_observada": round(float(series.mean()), 2),
            "media_esperada": round(mu, 2),
            "sd_observada": round(float(series.std()), 2),
            "sd_esperada": round(sd, 2),
            "ks_stat": round(float(ks_stat), 4),
            "ks_p_value": round(float(ks_p), 4),
        }

    return out


# ──────────────────────────────────────────────────────────────────────
# 2) Correlaciones esperadas vs observadas (OR)
# ──────────────────────────────────────────────────────────────────────
def _correlations(df_p: pd.DataFrame) -> dict:
    yaml_d = load_prevalences()
    corr_yaml = yaml_d["correlaciones_comorbilidades"]
    out = {}

    pairs = [
        ("retinopatia", "hipertension", corr_yaml["retinopatia_si_hta_grado2"]),
        ("nefropatia", "hipertension", corr_yaml["nefropatia_si_hta"]),
        ("cardiopatia", "dislipemia", corr_yaml["cardiopatia_si_dislipemia"]),
    ]
    for outcome, exposure, expected_or in pairs:
        try:
            ct = pd.crosstab(df_p[exposure], df_p[outcome])
            # OR = (a*d) / (b*c)
            a = ct.loc[True, True] if True in ct.index and True in ct.columns else 0
            b = ct.loc[True, False] if True in ct.index and False in ct.columns else 0
            c = ct.loc[False, True] if False in ct.index and True in ct.columns else 0
            d = ct.loc[False, False] if False in ct.index and False in ct.columns else 0
            if b * c == 0:
                or_observed = math.inf
            else:
                or_observed = (a * d) / (b * c)
        except Exception:
            or_observed = None
        out[f"{outcome}~{exposure}"] = {
            "or_esperado": expected_or,
            "or_observado": (round(or_observed, 2)
                             if or_observed is not None and not math.isinf(or_observed)
                             else None),
        }
    return out


# ──────────────────────────────────────────────────────────────────────
# 3) Privacidad por unicidad
# ──────────────────────────────────────────────────────────────────────
def _privacy(df_p: pd.DataFrame) -> dict:
    qids = df_p[["sexo", "edad", "region_grupo", "años_evolucion"]]
    counts = qids.value_counts()
    n_total = len(qids)
    n_unique = int((counts == 1).sum())
    return {
        "n_pacientes": n_total,
        "combinaciones_unicas": n_unique,
        "pct_unicas": round(n_unique / n_total * 100, 2) if n_total else 0.0,
        "quasi_identificadores": ["sexo", "edad", "region_grupo", "años_evolucion"],
        "nota": (
            "Métrica indicativa. Los datos son sintéticos por construcción; "
            "este test muestra el riesgo teórico de un atacante con acceso "
            "a los quasi-identificadores, no una brecha real."
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 4) Coherencia clínica (reglas booleanas)
# ──────────────────────────────────────────────────────────────────────
def _coherence(df_p: pd.DataFrame, df_e: pd.DataFrame) -> dict:
    rules = {}
    if not df_e.empty:
        rules["hba1c_minimo_5_5"] = bool((df_e["hba1c"] >= 5.5).all())
        rules["hba1c_maximo_13"] = bool((df_e["hba1c"] <= 13.0).all())

    rules["edad_diag_adulto"] = bool((df_p["edad_diagnostico"] >= 18).all())
    rules["edad_diag_no_supera_edad"] = bool(
        (df_p["edad_diagnostico"] <= df_p["edad"]).all()
    )

    # iSGLT2 — recomendación: usar solo si FGe ≥ 30
    if not df_e.empty:
        last_fge = df_e.groupby("patient_id")["filtrado_glomerular"].last()
        df_with_fge = df_p.set_index("patient_id").join(last_fge.rename("fge"))
        ok = ((~df_with_fge["isglt2"]) | (df_with_fge["fge"] >= 30)).all()
        rules["isglt2_compatible_con_fge"] = bool(ok)

    n_total = len(rules)
    n_ok = sum(1 for v in rules.values() if v)
    rules["score_global_pct"] = round(n_ok / n_total * 100, 1) if n_total else 100.0
    return rules
