"""Modelos Pydantic para configuración, paciente, encuentro y resultado."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SexDistribution = Literal["balanced", "real_world", "more_men", "more_women"]
RegionFocus = Literal["any", "alta", "media", "baja"]
OutputFormat = Literal["csv", "fhir", "omop", "all"]


class CohortConfig(BaseModel):
    """Parámetros de generación de cohorte (entrada del wizard)."""

    model_config = ConfigDict(extra="ignore")

    n_patients: int = Field(default=200, ge=50, le=10_000)
    edad_min: int = Field(default=18, ge=18, le=90)
    edad_max: int = Field(default=90, ge=18, le=90)
    sex_distribution: SexDistribution = "real_world"
    region_focus: RegionFocus = "any"
    forzar_comorbilidades: list[str] = Field(default_factory=list)
    excluir_comorbilidades: list[str] = Field(default_factory=list)
    generar_notas_clinicas: bool = False
    output_formats: list[OutputFormat] = Field(default_factory=lambda: ["csv"])
    seed: Optional[int] = None


class EncounterRecord(BaseModel):
    """Un encuentro clínico (visita) — biomarcadores en ese momento."""

    model_config = ConfigDict(extra="ignore")

    encounter_id: str
    patient_id: str
    encounter_date: datetime
    encounter_number: int      # 1 = primera visita
    hba1c: float
    glucemia_basal: int
    ldl: int
    hdl: int
    trigliceridos: int
    presion_sistolica: int
    presion_diastolica: int
    filtrado_glomerular: int
    imc: float
    nota_clinica: Optional[str] = None


class PatientRecord(BaseModel):
    """Paciente sintético — atributos estáticos + lista de encuentros."""

    model_config = ConfigDict(extra="ignore")

    patient_id: str
    nombre: str            # ficticio, generado por faker
    apellidos: str
    sexo: Literal["hombre", "mujer"]
    edad: int
    edad_grupo: str
    edad_diagnostico: int
    años_evolucion: int
    region: str
    region_grupo: str
    imc_grupo: str

    # Comorbilidades (si/no)
    hipertension: bool
    dislipemia: bool
    nefropatia: bool
    retinopatia: bool
    neuropatia: bool
    cardiopatia: bool

    # Tratamiento (si/no)
    metformina: bool
    insulina: bool
    sulfonilureas: bool
    idpp4: bool
    isglt2: bool
    arglp1: bool
    pioglitazona: bool

    encounters: list[EncounterRecord] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    """Salida del módulo `quality/`."""

    model_config = ConfigDict(extra="ignore")

    fidelidad_estadistica: dict
    correlaciones: dict
    privacidad_unicidad: dict
    coherencia_clinica: dict


class CohortDataset(BaseModel):
    """Resultado completo de una generación."""

    model_config = ConfigDict(extra="ignore")

    dataset_id: str
    created_at: datetime
    config: CohortConfig
    patients: list[PatientRecord]
    metrics: Optional[QualityMetrics] = None


class CohortJobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed"]
    progress: float = 0.0
    message: str = ""
    dataset_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
