"""LOINC — biomarcadores de laboratorio y mediciones clínicas."""

LOINC_SYSTEM = "http://loinc.org"

# Cada entrada incluye unidad UCUM canónica para FHIR Observation.valueQuantity
LABS_LOINC = {
    "hba1c":               {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood",  "unit": "%",       "ucum": "%"},
    "glucemia_basal":      {"code": "1558-6", "display": "Fasting glucose [Mass/volume] in Serum or Plasma", "unit": "mg/dL", "ucum": "mg/dL"},
    "ldl":                 {"code": "2089-1", "display": "LDL Cholesterol [Mass/volume] in Serum or Plasma", "unit": "mg/dL", "ucum": "mg/dL"},
    "hdl":                 {"code": "2085-9", "display": "HDL Cholesterol [Mass/volume] in Serum or Plasma", "unit": "mg/dL", "ucum": "mg/dL"},
    "trigliceridos":       {"code": "2571-8", "display": "Triglyceride [Mass/volume] in Serum or Plasma",    "unit": "mg/dL", "ucum": "mg/dL"},
    "presion_sistolica":   {"code": "8480-6", "display": "Systolic blood pressure",                          "unit": "mmHg",  "ucum": "mm[Hg]"},
    "presion_diastolica":  {"code": "8462-4", "display": "Diastolic blood pressure",                         "unit": "mmHg",  "ucum": "mm[Hg]"},
    "filtrado_glomerular": {"code": "33914-3","display": "Glomerular filtration rate/1.73 sq M.predicted",   "unit": "mL/min/1.73m2", "ucum": "mL/min/{1.73_m2}"},
    "imc":                 {"code": "39156-5","display": "Body mass index (BMI) [Ratio]",                    "unit": "kg/m2", "ucum": "kg/m2"},
    "creatinina":          {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma",      "unit": "mg/dL", "ucum": "mg/dL"},
}
