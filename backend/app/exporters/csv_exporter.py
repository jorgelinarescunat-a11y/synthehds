"""CSV plano — una fila por encuentro, todos los campos del paciente repetidos."""

from __future__ import annotations

import csv
import io
from typing import Iterable

from ..models.cohort import PatientRecord


CSV_COLUMNS = [
    "patient_id", "encounter_id", "encounter_number", "encounter_date",
    "nombre", "apellidos", "sexo", "edad", "edad_diagnostico",
    "años_evolucion", "region", "imc_grupo",
    "hba1c", "glucemia_basal", "ldl", "hdl", "trigliceridos",
    "presion_sistolica", "presion_diastolica", "filtrado_glomerular", "imc",
    "hipertension", "dislipemia", "nefropatia", "retinopatia",
    "neuropatia", "cardiopatia",
    "metformina", "insulina", "sulfonilureas", "idpp4",
    "isglt2", "arglp1", "pioglitazona",
    "nota_clinica",
]


def to_csv_rows(patients: Iterable[PatientRecord]) -> list[dict]:
    rows: list[dict] = []
    for p in patients:
        base = {
            "patient_id": p.patient_id,
            "nombre": p.nombre,
            "apellidos": p.apellidos,
            "sexo": p.sexo,
            "edad": p.edad,
            "edad_diagnostico": p.edad_diagnostico,
            "años_evolucion": p.años_evolucion,
            "region": p.region,
            "imc_grupo": p.imc_grupo,
            "hipertension": int(p.hipertension),
            "dislipemia": int(p.dislipemia),
            "nefropatia": int(p.nefropatia),
            "retinopatia": int(p.retinopatia),
            "neuropatia": int(p.neuropatia),
            "cardiopatia": int(p.cardiopatia),
            "metformina": int(p.metformina),
            "insulina": int(p.insulina),
            "sulfonilureas": int(p.sulfonilureas),
            "idpp4": int(p.idpp4),
            "isglt2": int(p.isglt2),
            "arglp1": int(p.arglp1),
            "pioglitazona": int(p.pioglitazona),
        }
        for enc in p.encounters:
            rows.append({
                **base,
                "encounter_id": enc.encounter_id,
                "encounter_number": enc.encounter_number,
                "encounter_date": enc.encounter_date.isoformat(),
                "hba1c": enc.hba1c,
                "glucemia_basal": enc.glucemia_basal,
                "ldl": enc.ldl,
                "hdl": enc.hdl,
                "trigliceridos": enc.trigliceridos,
                "presion_sistolica": enc.presion_sistolica,
                "presion_diastolica": enc.presion_diastolica,
                "filtrado_glomerular": enc.filtrado_glomerular,
                "imc": enc.imc,
                "nota_clinica": enc.nota_clinica or "",
            })
    return rows


def to_csv_string(patients: Iterable[PatientRecord]) -> str:
    rows = to_csv_rows(patients)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
