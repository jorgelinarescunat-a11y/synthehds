"""
Bayesian Network (pgmpy) para diabetes tipo 2 en España.

Esta red modela la coocurrencia entre demografía, control glucémico,
comorbilidades y tratamiento farmacológico. Cada CPT (Conditional
Probability Table) está derivada del YAML
`backend/app/data/diabetes_t2_spain.yaml` y lleva un comentario `fuente:`
que indica el valor exacto del YAML o, en su defecto, la justificación
literaria. Variables continuas (edad numérica, IMC, HbA1c, biomarcadores,
PA, FGe) se muestrean a posteriori condicionadas a las categorías
discretas devueltas por la red.

DAG (resumen):

    sexo ──────────────► edad_grupo
    sexo, edad_grupo ──► imc_grupo
    edad_grupo ────────► años_evol_grupo
    años_evol_grupo ───► hba1c_grupo
    imc_grupo ─────────► hipertension
    hba1c_grupo, años_evol_grupo ─────────► retinopatia
    hipertension, años_evol_grupo ─────────► nefropatia
    años_evol_grupo ──────────────────────► neuropatia
    hipertension, dislipemia (raíz) ──────► cardiopatia
    hba1c_grupo ──────────► metformina, insulina, sulfonilureas,
                            idpp4, pioglitazona
    hba1c_grupo, nefropatia ──────────────► isglt2
    hba1c_grupo, cardiopatia ─────────────► arglp1

`region_grupo` y `region` se muestrean fuera de la red (independiente
del cuadro clínico — el patrón norte/sur del YAML afecta a la prevalencia
global de DM2, no al perfil clínico una vez diagnosticado).
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
import pandas as pd
from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import BayesianNetwork
from pgmpy.sampling import BayesianModelSampling
from scipy.stats import truncnorm

from .yaml_loader import load_prevalences

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Estados discretos
# ──────────────────────────────────────────────────────────────────────
STATES: dict[str, list[str]] = {
    "sexo": ["hombre", "mujer"],
    "edad_grupo": ["18_40", "41_60", "61_75", "mayor_75"],
    "region_grupo": ["alta", "media", "baja"],
    "años_evol_grupo": ["corto", "medio", "largo"],
    "imc_grupo": ["normal", "sobrepeso", "obeso"],
    "hba1c_grupo": ["bueno", "moderado", "malo"],
    "hipertension": ["si", "no"],
    "dislipemia": ["si", "no"],
    "nefropatia": ["si", "no"],
    "retinopatia": ["si", "no"],
    "neuropatia": ["si", "no"],
    "cardiopatia": ["si", "no"],
    "metformina": ["si", "no"],
    "insulina": ["si", "no"],
    "sulfonilureas": ["si", "no"],
    "idpp4": ["si", "no"],
    "isglt2": ["si", "no"],
    "arglp1": ["si", "no"],
    "pioglitazona": ["si", "no"],
}

BINARY_COMORBIDITIES = [
    "hipertension", "dislipemia", "nefropatia",
    "retinopatia", "neuropatia", "cardiopatia",
]
DRUGS = [
    "metformina", "insulina", "sulfonilureas", "idpp4",
    "isglt2", "arglp1", "pioglitazona",
]

# Pirámide demográfica adulta española aproximada (≥18 años).
# Se usa SOLO para ponderar `prevalencia_por_edad_sexo` y obtener
# P(edad_grupo | sexo) en la población diabética.
# Fuente: INE 2023, padrón continuo (aproximación).
_AGE_PYRAMID_ADULT = {
    "18_40": 0.27,
    "41_60": 0.34,
    "61_75": 0.22,
    "mayor_75": 0.17,
}

# Pesos poblacionales de los tres grupos regionales (alta/media/baja
# prevalencia) ponderando población por CCAA — aproximación.
_REGION_GROUP_WEIGHTS = {"alta": 0.30, "media": 0.50, "baja": 0.20}


# ──────────────────────────────────────────────────────────────────────
# Helpers para CPTs binarias
# ──────────────────────────────────────────────────────────────────────
def _binary_rows(p_si: Sequence[float]) -> list[list[float]]:
    """Devuelve [[p_si...], [1-p_si...]] para una CPT binaria si/no."""
    p = list(p_si)
    return [p, [1.0 - x for x in p]]


# ══════════════════════════════════════════════════════════════════════
# CPTs
# ══════════════════════════════════════════════════════════════════════

def _cpt_sexo() -> TabularCPD:
    """
    P(sexo).
    fuente: aproximación. La DM2 muestra leve predominio masculino en los
    tramos 41-75 según [1] Di@bet.es Study, compensado en >75 por mayor
    longevidad femenina. Marginal usado: hombre 0.52, mujer 0.48.
    """
    return TabularCPD(
        variable="sexo",
        variable_card=2,
        values=[[0.52], [0.48]],
        state_names={"sexo": STATES["sexo"]},
    )


def _cpt_edad_grupo() -> TabularCPD:
    """
    P(edad_grupo | sexo).
    fuente: YAML.prevalencia_por_edad_sexo × pirámide adulta INE.
    Aplicando Bayes con P(diabético|edad,sexo) × P(edad|sexo)
    obtenemos la distribución de edad en el subconjunto diabético.
    """
    yaml_data = load_prevalences()
    prev = yaml_data["prevalencia_por_edad_sexo"]
    edad_states = STATES["edad_grupo"]

    cols = []
    for sex in STATES["sexo"]:
        weights = np.array(
            [prev[g][sex] * _AGE_PYRAMID_ADULT[g] for g in edad_states],
            dtype=float,
        )
        cols.append(weights / weights.sum())
    values = np.array(cols).T   # filas=edad_grupo, columnas=sexo

    return TabularCPD(
        variable="edad_grupo",
        variable_card=4,
        values=values.tolist(),
        evidence=["sexo"],
        evidence_card=[2],
        state_names={
            "edad_grupo": edad_states,
            "sexo": STATES["sexo"],
        },
    )


def _cpt_años_evol() -> TabularCPD:
    """
    P(años_evol_grupo | edad_grupo).
    fuente derivada: YAML.perfil_clinico_tipico
        edad_media_diagnostico = 58.97
        edad_media_paciente_actual = 70.0
        años_evolucion_media = 9.2 (σ 6.8)
    Los jóvenes (<40) sólo pueden haber sido diagnosticados recientemente;
    los pacientes >75 acumulan mayoritariamente >10 años de evolución.
    """
    # columnas: 18_40, 41_60, 61_75, mayor_75
    # filas:    corto (<5), medio (5-10), largo (>10)
    values = [
        [0.70, 0.35, 0.20, 0.15],   # corto
        [0.25, 0.40, 0.35, 0.30],   # medio
        [0.05, 0.25, 0.45, 0.55],   # largo
    ]
    return TabularCPD(
        variable="años_evol_grupo",
        variable_card=3,
        values=values,
        evidence=["edad_grupo"],
        evidence_card=[4],
        state_names={
            "años_evol_grupo": STATES["años_evol_grupo"],
            "edad_grupo": STATES["edad_grupo"],
        },
    )


def _cpt_imc_grupo() -> TabularCPD:
    """
    P(imc_grupo | sexo, edad_grupo).
    fuente: YAML.perfil_clinico_tipico.imc_medio = 29.86 (σ 4.8)
        y YAML.comorbilidades_pct.obesidad_imc_mayor30 = 35.
    Ajuste heurístico por (sexo, edad) — jóvenes hombres menor IMC,
    mujeres >75 mayor obesidad.
    """
    # columnas en orden lex: (hombre,18_40), (hombre,41_60), (hombre,61_75),
    # (hombre,mayor_75), (mujer,18_40), (mujer,41_60), (mujer,61_75),
    # (mujer,mayor_75).
    base = {"normal": 0.22, "sobrepeso": 0.43, "obeso": 0.35}
    deltas = {
        ("hombre", "18_40"):    {"normal": +0.10, "sobrepeso": +0.05, "obeso": -0.15},
        ("hombre", "41_60"):    {"normal": -0.05, "sobrepeso":  0.00, "obeso": +0.05},
        ("hombre", "61_75"):    {"normal": -0.05, "sobrepeso":  0.00, "obeso": +0.05},
        ("hombre", "mayor_75"): {"normal":  0.00, "sobrepeso": +0.05, "obeso": -0.05},
        ("mujer",  "18_40"):    {"normal": +0.08, "sobrepeso": +0.02, "obeso": -0.10},
        ("mujer",  "41_60"):    {"normal": -0.03, "sobrepeso":  0.00, "obeso": +0.03},
        ("mujer",  "61_75"):    {"normal": -0.05, "sobrepeso": -0.02, "obeso": +0.07},
        ("mujer",  "mayor_75"): {"normal": -0.08, "sobrepeso": -0.02, "obeso": +0.10},
    }
    cols = []
    for sex in STATES["sexo"]:
        for edad in STATES["edad_grupo"]:
            d = deltas[(sex, edad)]
            col = np.array([base[k] + d[k] for k in ("normal", "sobrepeso", "obeso")])
            col = np.clip(col, 0.02, 0.95)
            cols.append(col / col.sum())
    values = np.array(cols).T

    return TabularCPD(
        variable="imc_grupo",
        variable_card=3,
        values=values.tolist(),
        evidence=["sexo", "edad_grupo"],
        evidence_card=[2, 4],
        state_names={
            "imc_grupo": STATES["imc_grupo"],
            "sexo": STATES["sexo"],
            "edad_grupo": STATES["edad_grupo"],
        },
    )


def _cpt_hba1c_grupo() -> TabularCPD:
    """
    P(hba1c_grupo | años_evol_grupo).
    fuente: YAML.control_glucemico_hba1c (SIMETAP-DM)
        bueno  (<7)  = 63.4 %
        moder. (7-8) = 21.6 %
        malo   (≥8)  = 15.0 %
    Modulación por años de evolución — deterioro progresivo del control.
    """
    # columnas: corto, medio, largo
    values = [
        [0.72, 0.64, 0.55],   # bueno
        [0.18, 0.22, 0.25],   # moderado
        [0.10, 0.14, 0.20],   # malo
    ]
    return TabularCPD(
        variable="hba1c_grupo",
        variable_card=3,
        values=values,
        evidence=["años_evol_grupo"],
        evidence_card=[3],
        state_names={
            "hba1c_grupo": STATES["hba1c_grupo"],
            "años_evol_grupo": STATES["años_evol_grupo"],
        },
    )


def _cpt_hipertension() -> TabularCPD:
    """
    P(hipertension=si | imc_grupo).
    fuente: YAML.comorbilidades_pct.hipertension = 78.4 (marginal SIMETAP).
    Sube con obesidad (HTA y obesidad fuertemente correladas en DM2).
    """
    # columnas: imc_grupo = normal, sobrepeso, obeso
    p_si = [0.65, 0.78, 0.88]
    return TabularCPD(
        variable="hipertension",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["imc_grupo"],
        evidence_card=[3],
        state_names={
            "hipertension": STATES["hipertension"],
            "imc_grupo": STATES["imc_grupo"],
        },
    )


def _cpt_dislipemia() -> TabularCPD:
    """
    P(dislipemia) — raíz.
    fuente: YAML.comorbilidades_pct.dislipemia = 67.3 (SIMETAP).
    """
    return TabularCPD(
        variable="dislipemia",
        variable_card=2,
        values=[[0.673], [0.327]],
        state_names={"dislipemia": STATES["dislipemia"]},
    )


def _cpt_nefropatia() -> TabularCPD:
    """
    P(nefropatia=si | hipertension, años_evol_grupo).
    fuente: YAML.comorbilidades_pct.enfermedad_renal_cronica = 23.0
        + YAML.correlaciones_comorbilidades:
            nefropatia_si_hta = 3.0 (OR)
            nefropatia_si_años_evol_mayor10 = 2.8 (OR)
    """
    # columnas en orden lex:
    # (hta=si, ae=corto), (si, medio), (si, largo),
    # (no, corto),        (no, medio), (no, largo).
    p_si = [0.18, 0.28, 0.42, 0.07, 0.12, 0.20]
    return TabularCPD(
        variable="nefropatia",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["hipertension", "años_evol_grupo"],
        evidence_card=[2, 3],
        state_names={
            "nefropatia": STATES["nefropatia"],
            "hipertension": STATES["hipertension"],
            "años_evol_grupo": STATES["años_evol_grupo"],
        },
    )


def _cpt_retinopatia() -> TabularCPD:
    """
    P(retinopatia=si | hba1c_grupo, años_evol_grupo).
    fuente: YAML.comorbilidades_pct.retinopatia = 8.56 [4]
        + YAML.correlaciones_comorbilidades.retinopatia_si_hba1c_alta = 2.5.
    Aumenta marcadamente con peor control y mayor evolución.
    """
    # columnas en orden lex:
    # (hba1c=bueno,    ae=corto, medio, largo),
    # (hba1c=moderado, ae=corto, medio, largo),
    # (hba1c=malo,     ae=corto, medio, largo).
    p_si = [
        0.02, 0.05, 0.09,
        0.05, 0.10, 0.18,
        0.10, 0.18, 0.30,
    ]
    return TabularCPD(
        variable="retinopatia",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["hba1c_grupo", "años_evol_grupo"],
        evidence_card=[3, 3],
        state_names={
            "retinopatia": STATES["retinopatia"],
            "hba1c_grupo": STATES["hba1c_grupo"],
            "años_evol_grupo": STATES["años_evol_grupo"],
        },
    )


def _cpt_neuropatia() -> TabularCPD:
    """
    P(neuropatia=si | años_evol_grupo).
    fuente: YAML.comorbilidades_pct.neuropatia = 25.0.
    """
    p_si = [0.12, 0.25, 0.40]
    return TabularCPD(
        variable="neuropatia",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["años_evol_grupo"],
        evidence_card=[3],
        state_names={
            "neuropatia": STATES["neuropatia"],
            "años_evol_grupo": STATES["años_evol_grupo"],
        },
    )


def _cpt_cardiopatia() -> TabularCPD:
    """
    P(cardiopatia=si | hipertension, dislipemia).
    fuente: YAML.comorbilidades_pct.cardiopatia_isquemica = 12.0
        + YAML.correlaciones_comorbilidades.cardiopatia_si_dislipemia = 2.2.
    """
    # columnas: (hta=si, dl=si), (si, no), (no, si), (no, no)
    p_si = [0.18, 0.09, 0.10, 0.04]
    return TabularCPD(
        variable="cardiopatia",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["hipertension", "dislipemia"],
        evidence_card=[2, 2],
        state_names={
            "cardiopatia": STATES["cardiopatia"],
            "hipertension": STATES["hipertension"],
            "dislipemia": STATES["dislipemia"],
        },
    )


# ── Tratamiento ───────────────────────────────────────────────────────

def _binary_treatment_cpt(
    variable: str,
    p_si_by_hba1c: Sequence[float],
) -> TabularCPD:
    """P(fármaco | hba1c_grupo) — uso creciente con peor control."""
    return TabularCPD(
        variable=variable,
        variable_card=2,
        values=_binary_rows(p_si_by_hba1c),
        evidence=["hba1c_grupo"],
        evidence_card=[3],
        state_names={
            variable: STATES[variable],
            "hba1c_grupo": STATES["hba1c_grupo"],
        },
    )


def _cpt_metformina() -> TabularCPD:
    """
    P(metformina | hba1c_grupo).
    fuente: YAML.tratamiento_farmacologico_pct.metformina = 66.3 (RedgedapS).
    Base universal salvo contraindicación renal — sube ligeramente con
    peor control.
    """
    return _binary_treatment_cpt("metformina", [0.62, 0.68, 0.72])


def _cpt_insulina() -> TabularCPD:
    """
    P(insulina | hba1c_grupo).
    fuente: YAML.tratamiento_farmacologico_pct.insulina = 21.3.
    Aumenta marcadamente con HbA1c ≥ 8.
    """
    return _binary_treatment_cpt("insulina", [0.10, 0.25, 0.55])


def _cpt_sulfonilureas() -> TabularCPD:
    """
    P(sulfonilureas | hba1c_grupo).
    fuente: YAML.tratamiento_farmacologico_pct.sulfonilureas = 19.0
    (en declive, pero aún 19 % en RedgedapS).
    """
    return _binary_treatment_cpt("sulfonilureas", [0.16, 0.20, 0.24])


def _cpt_idpp4() -> TabularCPD:
    """
    P(idpp4 | hba1c_grupo).
    fuente: YAML.tratamiento_farmacologico_pct.idpp4 = 17.0.
    """
    return _binary_treatment_cpt("idpp4", [0.13, 0.18, 0.22])


def _cpt_pioglitazona() -> TabularCPD:
    """
    P(pioglitazona | hba1c_grupo).
    fuente: YAML.tratamiento_farmacologico_pct.pioglitazona = 3.0.
    """
    return _binary_treatment_cpt("pioglitazona", [0.02, 0.03, 0.05])


def _cpt_isglt2() -> TabularCPD:
    """
    P(isglt2 | hba1c_grupo, nefropatia).
    fuente: YAML.tratamiento_farmacologico_pct.isglt2 = 15.0
        + YAML.reglas_prescripcion: iSGLT2 preferente si ERC y FGe ≥ 30.
    """
    # columnas en orden lex: (bueno,si), (bueno,no), (moderado,si),
    # (moderado,no), (malo,si), (malo,no)
    p_si = [0.30, 0.10, 0.40, 0.15, 0.45, 0.18]
    return TabularCPD(
        variable="isglt2",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["hba1c_grupo", "nefropatia"],
        evidence_card=[3, 2],
        state_names={
            "isglt2": STATES["isglt2"],
            "hba1c_grupo": STATES["hba1c_grupo"],
            "nefropatia": STATES["nefropatia"],
        },
    )


def _cpt_arglp1() -> TabularCPD:
    """
    P(arglp1 | hba1c_grupo, cardiopatia).
    fuente: YAML.tratamiento_farmacologico_pct.arglp1 = 10.0
        + YAML.reglas_prescripcion: arGLP1 preferente si enfermedad
          cardiovascular u obesidad.
    """
    # columnas en orden lex: (bueno,si), (bueno,no), (moderado,si),
    # (moderado,no), (malo,si), (malo,no)
    p_si = [0.20, 0.06, 0.28, 0.10, 0.35, 0.13]
    return TabularCPD(
        variable="arglp1",
        variable_card=2,
        values=_binary_rows(p_si),
        evidence=["hba1c_grupo", "cardiopatia"],
        evidence_card=[3, 2],
        state_names={
            "arglp1": STATES["arglp1"],
            "hba1c_grupo": STATES["hba1c_grupo"],
            "cardiopatia": STATES["cardiopatia"],
        },
    )


# ══════════════════════════════════════════════════════════════════════
# Construcción de la red
# ══════════════════════════════════════════════════════════════════════
EDGES = [
    ("sexo", "edad_grupo"),
    ("edad_grupo", "años_evol_grupo"),
    ("sexo", "imc_grupo"),
    ("edad_grupo", "imc_grupo"),
    ("imc_grupo", "hipertension"),
    ("años_evol_grupo", "hba1c_grupo"),
    ("hba1c_grupo", "retinopatia"),
    ("años_evol_grupo", "retinopatia"),
    ("hipertension", "nefropatia"),
    ("años_evol_grupo", "nefropatia"),
    ("años_evol_grupo", "neuropatia"),
    ("hipertension", "cardiopatia"),
    ("dislipemia", "cardiopatia"),
    ("hba1c_grupo", "metformina"),
    ("hba1c_grupo", "insulina"),
    ("hba1c_grupo", "sulfonilureas"),
    ("hba1c_grupo", "idpp4"),
    ("hba1c_grupo", "pioglitazona"),
    ("hba1c_grupo", "isglt2"),
    ("nefropatia", "isglt2"),
    ("hba1c_grupo", "arglp1"),
    ("cardiopatia", "arglp1"),
]


def build_network() -> BayesianNetwork:
    """Construye la BN con todos los nodos y CPTs y valida la consistencia."""
    model = BayesianNetwork(EDGES)
    cpts = [
        _cpt_sexo(),
        _cpt_edad_grupo(),
        _cpt_años_evol(),
        _cpt_imc_grupo(),
        _cpt_hba1c_grupo(),
        _cpt_hipertension(),
        _cpt_dislipemia(),
        _cpt_nefropatia(),
        _cpt_retinopatia(),
        _cpt_neuropatia(),
        _cpt_cardiopatia(),
        _cpt_metformina(),
        _cpt_insulina(),
        _cpt_sulfonilureas(),
        _cpt_idpp4(),
        _cpt_pioglitazona(),
        _cpt_isglt2(),
        _cpt_arglp1(),
    ]
    model.add_cpds(*cpts)
    assert model.check_model(), "BN inválida — revisar CPTs y aristas"
    return model


# ══════════════════════════════════════════════════════════════════════
# Muestreo: categorías discretas → DataFrame con variables continuas
# ══════════════════════════════════════════════════════════════════════
def sample_cohort(
    n_patients: int = 100,
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Muestrea `n_patients` pacientes mediante forward sampling de la BN
    y completa con variables continuas calibradas desde el YAML.

    Devuelve un DataFrame con una fila por paciente y columnas tanto
    categóricas (sufijo `_grupo`) como continuas (edad numérica, IMC,
    HbA1c %, glucemia, lípidos, presión arterial, FGe).
    """
    if seed is not None:
        np.random.seed(seed)

    model = build_network()
    sampler = BayesianModelSampling(model)
    try:
        discrete = sampler.forward_sample(size=n_patients, show_progress=False)
    except TypeError:
        # Algunas versiones antiguas de pgmpy no soportan show_progress
        discrete = sampler.forward_sample(size=n_patients)

    return _add_continuous_variables(discrete, seed=seed)


def _add_continuous_variables(
    df: pd.DataFrame,
    seed: int | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    yaml_data = load_prevalences()
    bio = yaml_data["biomarcadores_distribucion"]

    out = df.copy()
    n = len(out)

    # ── Edad numérica dentro del grupo
    age_range = {
        "18_40": (18, 40),
        "41_60": (41, 60),
        "61_75": (61, 75),
        "mayor_75": (76, 90),
    }
    out["edad"] = [
        int(rng.integers(age_range[g][0], age_range[g][1] + 1))
        for g in out["edad_grupo"]
    ]

    # ── Años de evolución (cap por edad — dx no puede ser antes de 18 años)
    evol_range = {"corto": (0, 4), "medio": (5, 10), "largo": (11, 30)}

    def _sample_evol(row) -> int:
        lo, hi = evol_range[row["años_evol_grupo"]]
        max_evol = max(0, int(row["edad"]) - 18)
        hi = min(hi, max_evol)
        if hi < lo:
            return max_evol
        return int(rng.integers(lo, hi + 1))

    out["años_evolucion"] = out.apply(_sample_evol, axis=1)
    out["edad_diagnostico"] = out["edad"] - out["años_evolucion"]

    # ── IMC kg/m² — media por grupo, σ ≈ 1.7
    imc_means = {"normal": 23.0, "sobrepeso": 27.5, "obeso": 33.0}
    out["imc"] = [
        round(_truncnorm_one(imc_means[g], 1.7, 16, 55, rng), 1)
        for g in out["imc_grupo"]
    ]

    # ── HbA1c % — media por grupo, σ ≈ 0.6, truncada al rango YAML
    hba1c_means = {"bueno": 6.5, "moderado": 7.5, "malo": 9.2}
    h_lo, h_hi = yaml_data["control_glucemico_hba1c"]["rango_realista"]
    out["hba1c"] = [
        round(_truncnorm_one(hba1c_means[g], 0.6, h_lo, h_hi, rng), 1)
        for g in out["hba1c_grupo"]
    ]

    # ── Glucemia basal mg/dL — correlacionada con HbA1c
    # (aprox lineal: glucemia ≈ 28·HbA1c − 60)
    gl_cfg = bio["glucemia_basal_mg_dl"]
    gl_mean_from_hba1c = 28.0 * out["hba1c"].to_numpy() - 60.0
    noise = rng.normal(0, gl_cfg["desv"] * 0.5, size=n)
    out["glucemia_basal"] = np.clip(
        gl_mean_from_hba1c + noise, gl_cfg["rango"][0], gl_cfg["rango"][1],
    ).round(0).astype(int)

    # ── LDL mg/dL
    out["ldl"] = _truncnorm_array(
        bio["ldl_mg_dl"]["media"], bio["ldl_mg_dl"]["desv"],
        bio["ldl_mg_dl"]["rango"][0], bio["ldl_mg_dl"]["rango"][1], n, rng,
    ).round(0).astype(int)

    # ── HDL mg/dL — dependiente del sexo
    out["hdl"] = [
        int(round(_truncnorm_one(
            bio["hdl_mg_dl"][s]["media"],
            bio["hdl_mg_dl"][s]["desv"],
            25, 100, rng,
        )))
        for s in out["sexo"]
    ]

    # ── Triglicéridos
    out["trigliceridos"] = _truncnorm_array(
        bio["trigliceridos_mg_dl"]["media"], bio["trigliceridos_mg_dl"]["desv"],
        bio["trigliceridos_mg_dl"]["rango"][0], bio["trigliceridos_mg_dl"]["rango"][1],
        n, rng,
    ).round(0).astype(int)

    # ── Presión arterial — shift si HTA
    ps = bio["presion_sistolica_mmhg"]
    pd_ = bio["presion_diastolica_mmhg"]
    hta_si = (out["hipertension"].to_numpy() == "si")
    sis_shift = np.where(hta_si, 8.0, -4.0)
    dia_shift = np.where(hta_si, 5.0, -2.0)
    out["presion_sistolica"] = np.clip(
        rng.normal(ps["media"], ps["desv"], n) + sis_shift, 90, 210,
    ).round(0).astype(int)
    out["presion_diastolica"] = np.clip(
        rng.normal(pd_["media"], pd_["desv"], n) + dia_shift, 50, 130,
    ).round(0).astype(int)

    # ── Filtrado glomerular — bajada marcada si nefropatía
    fg = bio["filtrado_glomerular_ml_min"]
    nefro_si = (out["nefropatia"].to_numpy() == "si")
    fge_shift = np.where(nefro_si, -25.0, 5.0)
    out["filtrado_glomerular"] = np.clip(
        rng.normal(fg["media"], fg["desv"], n) + fge_shift, 10, 130,
    ).round(0).astype(int)

    # ── Región (muestreo marginal independiente del cuadro clínico)
    region_groups_order = ["alta", "media", "baja"]
    region_weights = np.array(
        [_REGION_GROUP_WEIGHTS[g] for g in region_groups_order]
    )
    out["region_grupo"] = rng.choice(
        region_groups_order, size=n, p=region_weights,
    )

    region_lookup = {
        "alta":  yaml_data["variacion_regional"]["prevalencia_alta"],
        "media": yaml_data["variacion_regional"]["prevalencia_media"],
        "baja":  yaml_data["variacion_regional"]["prevalencia_baja"],
    }
    out["region"] = [
        str(rng.choice(region_lookup[g])) for g in out["region_grupo"]
    ]

    return out


# ──────────────────────────────────────────────────────────────────────
# Utilidades de muestreo continuo
# ──────────────────────────────────────────────────────────────────────
def _truncnorm_one(mean: float, sd: float, low: float, high: float, rng) -> float:
    a, b = (low - mean) / sd, (high - mean) / sd
    return float(truncnorm.rvs(a, b, loc=mean, scale=sd, random_state=rng))


def _truncnorm_array(
    mean: float, sd: float, low: float, high: float, n: int, rng,
) -> np.ndarray:
    a, b = (low - mean) / sd, (high - mean) / sd
    return truncnorm.rvs(a, b, loc=mean, scale=sd, size=n, random_state=rng)
