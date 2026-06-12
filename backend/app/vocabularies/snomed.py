"""SNOMED-CT — códigos para DM2 y comorbilidades habituales."""

SNOMED_SYSTEM = "http://snomed.info/sct"

CONDITIONS_SNOMED = {
    "diabetes_t2":            {"code": "44054006",  "display": "Diabetes mellitus type 2"},
    "diabetes_t2_renal":      {"code": "127013003", "display": "Diabetic renal disease"},
    "diabetes_t2_retino":     {"code": "4855003",   "display": "Diabetic retinopathy"},
    "diabetes_t2_neuro":      {"code": "230572002", "display": "Diabetic neuropathy"},
    "hipertension":           {"code": "38341003",  "display": "Hypertensive disorder, systemic arterial"},
    "dislipemia":             {"code": "370992007", "display": "Dyslipidemia"},
    "nefropatia":             {"code": "709044004", "display": "Chronic kidney disease"},
    "retinopatia":            {"code": "4855003",   "display": "Diabetic retinopathy"},
    "neuropatia":             {"code": "230572002", "display": "Diabetic neuropathy"},
    "cardiopatia":            {"code": "414545008", "display": "Ischemic heart disease"},
    "insuficiencia_cardiaca": {"code": "84114007",  "display": "Heart failure"},
    "ictus_previo":           {"code": "230690007", "display": "Cerebrovascular accident"},
    "obesidad":               {"code": "414916001", "display": "Obesity"},
}
