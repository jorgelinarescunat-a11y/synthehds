"""ICD-10-CM — códigos para DM2 y comorbilidades habituales."""

ICD10_SYSTEM = "http://hl7.org/fhir/sid/icd-10-cm"

CONDITIONS_ICD10 = {
    "diabetes_t2":          {"code": "E11.9",  "display": "Type 2 diabetes mellitus without complications"},
    "diabetes_t2_renal":    {"code": "E11.22", "display": "Type 2 diabetes mellitus with diabetic chronic kidney disease"},
    "diabetes_t2_retino":   {"code": "E11.319","display": "Type 2 DM with unspecified diabetic retinopathy"},
    "diabetes_t2_neuro":    {"code": "E11.40", "display": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified"},
    "hipertension":         {"code": "I10",    "display": "Essential (primary) hypertension"},
    "dislipemia":           {"code": "E78.5",  "display": "Hyperlipidemia, unspecified"},
    "nefropatia":           {"code": "N18.9",  "display": "Chronic kidney disease, unspecified"},
    "retinopatia":          {"code": "H36",    "display": "Retinal disorders in diseases classified elsewhere"},
    "neuropatia":           {"code": "G63.2",  "display": "Diabetic polyneuropathy"},
    "cardiopatia":          {"code": "I25.9",  "display": "Chronic ischemic heart disease, unspecified"},
    "insuficiencia_cardiaca": {"code": "I50.9", "display": "Heart failure, unspecified"},
    "ictus_previo":         {"code": "I69.9",  "display": "Sequelae of unspecified cerebrovascular disease"},
    "obesidad":             {"code": "E66.9",  "display": "Obesity, unspecified"},
}
