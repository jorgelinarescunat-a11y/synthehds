"""ATC (WHO) — fármacos antidiabéticos del modelo."""

ATC_SYSTEM = "http://www.whocc.no/atc"

DRUGS_ATC = {
    "metformina":    {"code": "A10BA02", "display": "Metformin"},
    "insulina":      {"code": "A10AB",   "display": "Insulin, fast-acting"},
    "sulfonilureas": {"code": "A10BB",   "display": "Sulfonylureas"},
    "idpp4":         {"code": "A10BH",   "display": "Dipeptidyl peptidase-4 (DPP-4) inhibitors"},
    "isglt2":        {"code": "A10BK",   "display": "Sodium-glucose co-transporter 2 (SGLT2) inhibitors"},
    "arglp1":        {"code": "A10BJ",   "display": "Glucagon-like peptide-1 (GLP-1) analogues"},
    "pioglitazona":  {"code": "A10BG03", "display": "Pioglitazone"},
}
