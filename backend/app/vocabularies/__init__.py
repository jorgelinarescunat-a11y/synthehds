"""Diccionarios de códigos clínicos estándar usados por los exportadores.

Cada vocabulario expone:
    `CONDITIONS_*`     — mapeo condición YAML → código
    `DRUGS_*`          — mapeo fármaco YAML → código
    `LABS_*` / `MEAS_*` — mapeo biomarcador YAML → código

Los valores aquí son una selección representativa para diabetes T2;
no pretenden ser un catálogo exhaustivo. Se documentan las URI canónicas
de cada sistema para que los exportadores FHIR/OMOP las usen sin
hard-codear strings en otros módulos.
"""

from .icd10 import CONDITIONS_ICD10, ICD10_SYSTEM
from .snomed import CONDITIONS_SNOMED, SNOMED_SYSTEM
from .atc import DRUGS_ATC, ATC_SYSTEM
from .loinc import LABS_LOINC, LOINC_SYSTEM

__all__ = [
    "CONDITIONS_ICD10", "ICD10_SYSTEM",
    "CONDITIONS_SNOMED", "SNOMED_SYSTEM",
    "DRUGS_ATC", "ATC_SYSTEM",
    "LABS_LOINC", "LOINC_SYSTEM",
]
