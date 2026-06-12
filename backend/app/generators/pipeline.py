"""
Pipeline completo de generación de una cohorte DM2.

Combina:
  1. Forward sampling de la Bayesian Network (`bayesian_model.sample_cohort`).
  2. Identificadores sintéticos con `faker` (NUNCA datos reales: nombre y
     apellido ficticios; el ID es un UUID v4 — no genera DNIs).
  3. Filtros opcionales: rango etario, distribución de sexo, región,
     forzar/excluir comorbilidades.
  4. Serie temporal de 3-5 encuentros por paciente con evolución
     estocástica de biomarcadores. La HbA1c tiende a mejorar si el
     tratamiento es coherente con las reglas del YAML y a empeorar si no
     hay adherencia (probabilidad 20 %).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from faker import Faker

from ..models.cohort import (
    CohortConfig,
    EncounterRecord,
    PatientRecord,
)
from .bayesian_model import sample_cohort
from .yaml_loader import load_prevalences

logger = logging.getLogger(__name__)

_FAKER = Faker("es_ES")

# Probabilidad de no adherencia en cualquier encuentro → la HbA1c sube
# en lugar de bajar entre visitas.
_NON_ADHERENCE_PROB = 0.20

# Número de encuentros por paciente
_ENCOUNTERS_MIN = 3
_ENCOUNTERS_MAX = 5


# ──────────────────────────────────────────────────────────────────────
# Pipeline público
# ──────────────────────────────────────────────────────────────────────
def generate_cohort(config: CohortConfig) -> list[PatientRecord]:
    """Genera una cohorte completa según `config`. Devuelve lista de pacientes."""
    seed = config.seed
    if seed is not None:
        np.random.seed(seed)
        Faker.seed(seed)
    rng = np.random.default_rng(seed)

    # 1. Forward sampling de la BN — sobremuestreamos para tener margen
    #    tras aplicar filtros de edad/sexo/región/comorbilidades.
    oversample_factor = _estimate_oversample(config)
    candidate_n = int(config.n_patients * oversample_factor)
    df = sample_cohort(n_patients=candidate_n, seed=seed)

    # 2. Aplicar filtros configurables
    df = _apply_filters(df, config, rng)

    if len(df) < config.n_patients:
        logger.warning(
            "Solo %d pacientes superan los filtros (objetivo %d) — "
            "se devuelven todos los disponibles.",
            len(df), config.n_patients,
        )
    df = df.head(config.n_patients).reset_index(drop=True)

    # 3. Identificadores sintéticos + estructura Pydantic
    patients: list[PatientRecord] = []
    for _, row in df.iterrows():
        patient = _row_to_patient(row, rng)
        patient.encounters = _generate_encounters(patient, row, rng)
        patients.append(patient)
    return patients


# ──────────────────────────────────────────────────────────────────────
# Filtros
# ──────────────────────────────────────────────────────────────────────
def _estimate_oversample(config: CohortConfig) -> float:
    """Factor de sobremuestreo para compensar pérdida por filtros."""
    factor = 1.4
    age_span = (config.edad_max - config.edad_min) / 72.0
    factor /= max(age_span, 0.2)
    if config.region_focus != "any":
        factor *= 2.5
    if config.forzar_comorbilidades:
        # Cada comorbilidad forzada con prev ~30 % triplica aprox.
        factor *= 1 + 1.5 * len(config.forzar_comorbilidades)
    return min(factor, 20.0)


def _apply_filters(
    df: pd.DataFrame, config: CohortConfig, rng: np.random.Generator,
) -> pd.DataFrame:
    out = df.copy()

    # Edad
    out = out[(out["edad"] >= config.edad_min) & (out["edad"] <= config.edad_max)]

    # Región
    if config.region_focus != "any":
        out = out[out["region_grupo"] == config.region_focus]

    # Distribución de sexo
    if config.sex_distribution != "real_world":
        out = _rebalance_sex(out, config.sex_distribution, rng)

    # Comorbilidades forzadas
    for cm in config.forzar_comorbilidades:
        if cm in out.columns:
            out = out[out[cm] == "si"]
    # Comorbilidades excluidas
    for cm in config.excluir_comorbilidades:
        if cm in out.columns:
            out = out[out[cm] == "no"]

    return out.reset_index(drop=True)


def _rebalance_sex(
    df: pd.DataFrame, distribution: str, rng: np.random.Generator,
) -> pd.DataFrame:
    if distribution == "balanced":
        target_male = 0.50
    elif distribution == "more_men":
        target_male = 0.70
    elif distribution == "more_women":
        target_male = 0.30
    else:
        return df

    men = df[df["sexo"] == "hombre"]
    women = df[df["sexo"] == "mujer"]
    n_target = min(len(df), max(len(men), len(women)) * 2)
    n_men = int(round(n_target * target_male))
    n_women = n_target - n_men

    men_sample = men.sample(min(n_men, len(men)), random_state=int(rng.integers(0, 2**31)))
    women_sample = women.sample(min(n_women, len(women)), random_state=int(rng.integers(0, 2**31)))
    return pd.concat([men_sample, women_sample]).sample(
        frac=1, random_state=int(rng.integers(0, 2**31))
    ).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────────
# Conversión BN → PatientRecord
# ──────────────────────────────────────────────────────────────────────
def _row_to_patient(row: pd.Series, rng: np.random.Generator) -> PatientRecord:
    sexo = row["sexo"]
    if sexo == "hombre":
        nombre = _FAKER.first_name_male()
    else:
        nombre = _FAKER.first_name_female()
    apellidos = f"{_FAKER.last_name()} {_FAKER.last_name()}"

    return PatientRecord(
        patient_id=str(uuid.uuid4()),
        nombre=nombre,
        apellidos=apellidos,
        sexo=sexo,
        edad=int(row["edad"]),
        edad_grupo=row["edad_grupo"],
        edad_diagnostico=int(row["edad_diagnostico"]),
        años_evolucion=int(row["años_evolucion"]),
        region=row["region"],
        region_grupo=row["region_grupo"],
        imc_grupo=row["imc_grupo"],
        hipertension=row["hipertension"] == "si",
        dislipemia=row["dislipemia"] == "si",
        nefropatia=row["nefropatia"] == "si",
        retinopatia=row["retinopatia"] == "si",
        neuropatia=row["neuropatia"] == "si",
        cardiopatia=row["cardiopatia"] == "si",
        metformina=row["metformina"] == "si",
        insulina=row["insulina"] == "si",
        sulfonilureas=row["sulfonilureas"] == "si",
        idpp4=row["idpp4"] == "si",
        isglt2=row["isglt2"] == "si",
        arglp1=row["arglp1"] == "si",
        pioglitazona=row["pioglitazona"] == "si",
    )


# ──────────────────────────────────────────────────────────────────────
# Encuentros longitudinales
# ──────────────────────────────────────────────────────────────────────
def _generate_encounters(
    patient: PatientRecord,
    row: pd.Series,
    rng: np.random.Generator,
) -> list[EncounterRecord]:
    """
    Genera 3-5 encuentros distribuidos en 1-3 años. La HbA1c y los
    biomarcadores evolucionan estocásticamente — mejora si tratamiento
    coherente, empeora con prob `_NON_ADHERENCE_PROB`.
    """
    yaml_data = load_prevalences()
    h_lo, h_hi = yaml_data["control_glucemico_hba1c"]["rango_realista"]

    n_encounters = int(rng.integers(_ENCOUNTERS_MIN, _ENCOUNTERS_MAX + 1))
    today = datetime.now(timezone.utc)
    total_span_days = int(rng.integers(365, 365 * 3 + 1))
    start = today - timedelta(days=total_span_days)

    # Estado basal: tomamos los biomarcadores de la fila BN
    hba1c = float(row["hba1c"])
    glucemia = int(row["glucemia_basal"])
    ldl = int(row["ldl"])
    hdl = int(row["hdl"])
    tg = int(row["trigliceridos"])
    sis = int(row["presion_sistolica"])
    dia = int(row["presion_diastolica"])
    fge = int(row["filtrado_glomerular"])
    imc = float(row["imc"])

    # Tendencia: mejora si tratamiento coherente con HbA1c, empeora si no
    treatment_coherent = (
        patient.metformina or patient.insulina or patient.idpp4 or
        patient.isglt2 or patient.arglp1
    )

    encounters: list[EncounterRecord] = []
    for i in range(n_encounters):
        # Espaciado uniforme + jitter ±20 días
        day_offset = int(i * (total_span_days / max(n_encounters - 1, 1))) \
            if n_encounters > 1 else 0
        day_offset += int(rng.integers(-20, 21))
        day_offset = max(0, min(day_offset, total_span_days))
        enc_date = start + timedelta(days=day_offset)

        # Evolución HbA1c
        if i > 0:
            non_adherent = rng.random() < _NON_ADHERENCE_PROB
            if non_adherent or not treatment_coherent:
                delta = float(rng.normal(0.15, 0.20))
            else:
                delta = float(rng.normal(-0.10, 0.20))
            hba1c = float(np.clip(hba1c + delta, h_lo, h_hi))
            # Glucemia sigue HbA1c
            glucemia = int(np.clip(28 * hba1c - 60 + rng.normal(0, 12), 70, 350))
            # Otros biomarcadores con drift suave
            ldl = int(np.clip(ldl + rng.normal(0, 8), 40, 250))
            hdl = int(np.clip(hdl + rng.normal(0, 3), 25, 100))
            tg = int(np.clip(tg + rng.normal(0, 20), 50, 600))
            sis = int(np.clip(sis + rng.normal(0, 4), 90, 210))
            dia = int(np.clip(dia + rng.normal(0, 3), 50, 130))
            if patient.nefropatia:
                fge = int(np.clip(fge + rng.normal(-1.5, 2), 10, 130))
            else:
                fge = int(np.clip(fge + rng.normal(0, 2), 10, 130))
            imc = round(float(np.clip(imc + rng.normal(0, 0.3), 16, 55)), 1)

        encounters.append(EncounterRecord(
            encounter_id=str(uuid.uuid4()),
            patient_id=patient.patient_id,
            encounter_date=enc_date,
            encounter_number=i + 1,
            hba1c=round(hba1c, 1),
            glucemia_basal=glucemia,
            ldl=ldl,
            hdl=hdl,
            trigliceridos=tg,
            presion_sistolica=sis,
            presion_diastolica=dia,
            filtrado_glomerular=fge,
            imc=imc,
        ))
    return encounters
