"""
Data Sheet PDF (reportlab) que acompaña a cada dataset generado.

Contenido obligatorio:
  - Parámetros de generación
  - Metodología (BN + reglas clínicas + Claude para narrativa)
  - **Las 5 fuentes científicas citadas íntegramente**
  - Métricas de calidad
  - Declaración legal EHDS
  - UUID del dataset, timestamp ISO 8601, versión del software
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
)

from ..models.cohort import CohortConfig, QualityMetrics

SOFTWARE_VERSION = "SynthEHDS 0.1.0 (MVP)"

CITATIONS = [
    ("[1]", "Soriguer F, Goday A, Bosch-Comas A, et al. "
            "Prevalence of diabetes mellitus and impaired glucose regulation "
            "in Spain: the Di@bet.es Study. "
            "Diabetologia. 2012;55:88-93."),
    ("[2]", "Ministerio de Sanidad. Prevalencia de diabetes mellitus en 2016 "
            "en España según la Base de Datos Clínicos de Atención Primaria (BDCAP). "
            "Endocrinología, Diabetes y Nutrición. 2021. "
            "DOI: 10.1016/j.endinu.2020.03.019"),
    ("[3]", "Ruiz-García A, et al. Prevalencia de diabetes mellitus en el ámbito "
            "de la atención primaria española y su asociación con factores de riesgo "
            "cardiovascular. Estudio SIMETAP-DM. "
            "Clínica e Investigación en Arteriosclerosis. 2020."),
    ("[4]", "Estudio Cantabria sobre retinopatía diabética. "
            "Atención Primaria. 2020. DOI: 10.1016/j.aprim.2018.09.004"),
    ("[5]", "Mata-Cases M et al. RedgedapS. Características clínicas y "
            "tratamiento antidiabético en DM2 en atención primaria española. "
            "Medicina de Familia SEMERGEN. 2021."),
]

EHDS_DISCLAIMER = (
    "Este dataset es completamente sintético. No deriva de, ni ha sido entrenado "
    "con, datos reales identificables de pacientes. Los valores provienen de "
    "distribuciones estadísticas y reglas clínicas codificadas desde literatura "
    "científica pública. No es válido para conclusiones clínicas, exclusivamente "
    "para prototipado de modelos de IA, formación e investigación metodológica. "
    "Generado conforme a los principios del European Health Data Space (EHDS) "
    "para uso secundario de datos."
)

METHODOLOGY = (
    "Enfoque híbrido en cuatro capas:\n"
    "1) Distribuciones estadísticas extraídas de literatura epidemiológica "
    "española (ver fuentes [1]-[5]).\n"
    "2) Reglas clínicas codificadas desde guías de práctica clínica.\n"
    "3) Bayesian Network (pgmpy) para modelar correlaciones entre demografía, "
    "biomarcadores, comorbilidades y tratamiento. Cada CPT está derivada de "
    "valores específicos del YAML de prevalencias.\n"
    "4) Claude (Anthropic API) usado únicamente para narrativa clínica en "
    "español (notas SOAP). Nunca para generación estadística ni entrenado con "
    "datos reales."
)


def build_datasheet(
    dataset_id: str,
    config: CohortConfig,
    metrics: QualityMetrics,
    n_patients: int,
    n_encounters: int,
) -> bytes:
    """Devuelve el PDF como bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"SynthEHDS Data Sheet — {dataset_id}",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13,
                        spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1f4e79"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10,
                          leading=14, spaceAfter=4)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=9,
                           leading=12, spaceAfter=2)

    elements: list = []

    # ── Header ───────────────────────────────────────────────────────
    elements.append(Paragraph("SynthEHDS — Data Sheet", h1))
    elements.append(Paragraph(
        f"<b>Dataset ID:</b> {dataset_id}<br/>"
        f"<b>Generado:</b> {datetime.now(timezone.utc).isoformat()}<br/>"
        f"<b>Software:</b> {SOFTWARE_VERSION}",
        body,
    ))
    elements.append(Spacer(1, 8))

    # ── 1. Parámetros ────────────────────────────────────────────────
    elements.append(Paragraph("1. Parámetros de generación", h2))
    params_data = [
        ["Parámetro", "Valor"],
        ["N° pacientes solicitados", str(config.n_patients)],
        ["N° pacientes generados", str(n_patients)],
        ["N° total de encuentros", str(n_encounters)],
        ["Rango etario", f"{config.edad_min} – {config.edad_max}"],
        ["Distribución de sexo", config.sex_distribution],
        ["Foco regional", config.region_focus],
        ["Comorbilidades forzadas",
         ", ".join(config.forzar_comorbilidades) or "—"],
        ["Comorbilidades excluidas",
         ", ".join(config.excluir_comorbilidades) or "—"],
        ["Notas clínicas (Claude)",
         "sí" if config.generar_notas_clinicas else "no"],
        ["Formatos de salida",
         ", ".join(config.output_formats)],
        ["Seed reproducibilidad", str(config.seed) if config.seed is not None else "aleatorio"],
    ]
    elements.append(_styled_table(params_data))

    # ── 2. Metodología ───────────────────────────────────────────────
    elements.append(Paragraph("2. Metodología", h2))
    for line in METHODOLOGY.split("\n"):
        elements.append(Paragraph(line, body))

    # ── 3. Fuentes científicas ───────────────────────────────────────
    elements.append(Paragraph("3. Fuentes científicas", h2))
    for tag, citation in CITATIONS:
        elements.append(Paragraph(f"<b>{tag}</b> {citation}", small))

    elements.append(PageBreak())

    # ── 4. Métricas de calidad ───────────────────────────────────────
    elements.append(Paragraph("4. Métricas de calidad", h2))

    elements.append(Paragraph("4.1 Fidelidad estadística — variables categóricas", body))
    cat_rows = [["Variable", "Observado %", "Esperado %", "Δ pp", "p-value (chi²)"]]
    for var, data in metrics.fidelidad_estadistica.get("categoricas", {}).items():
        cat_rows.append([
            var, str(data["observado_pct"]), str(data["esperado_pct"]),
            str(data["diff_pp"]), str(data["p_value"]),
        ])
    elements.append(_styled_table(cat_rows))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("4.2 Fidelidad estadística — variables continuas", body))
    cont_rows = [["Variable", "μ obs", "μ esp", "σ obs", "σ esp", "KS p-value"]]
    for var, data in metrics.fidelidad_estadistica.get("continuas", {}).items():
        cont_rows.append([
            var, str(data["media_observada"]), str(data["media_esperada"]),
            str(data["sd_observada"]), str(data["sd_esperada"]),
            str(data["ks_p_value"]),
        ])
    elements.append(_styled_table(cont_rows))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("4.3 Correlaciones (Odds Ratios)", body))
    or_rows = [["Pareja", "OR esperado", "OR observado"]]
    for pair, vals in metrics.correlaciones.items():
        or_rows.append([
            pair, str(vals["or_esperado"]),
            str(vals["or_observado"]) if vals["or_observado"] is not None else "n/d",
        ])
    elements.append(_styled_table(or_rows))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("4.4 Privacidad — unicidad de quasi-identificadores", body))
    priv = metrics.privacidad_unicidad
    elements.append(Paragraph(
        f"{priv['combinaciones_unicas']} / {priv['n_pacientes']} pacientes "
        f"con combinación única ({priv['pct_unicas']} %). "
        f"Quasi-IDs: {', '.join(priv['quasi_identificadores'])}.",
        small,
    ))
    elements.append(Paragraph(priv["nota"], small))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("4.5 Coherencia clínica (reglas booleanas)", body))
    coh_rows = [["Regla", "OK"]]
    for k, v in metrics.coherencia_clinica.items():
        if k == "score_global_pct":
            continue
        coh_rows.append([k, "✓" if v else "✗"])
    coh_rows.append(["Score global", f"{metrics.coherencia_clinica['score_global_pct']} %"])
    elements.append(_styled_table(coh_rows))

    # ── 5. Declaración legal ─────────────────────────────────────────
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("5. Declaración legal (EHDS)", h2))
    elements.append(Paragraph(EHDS_DISCLAIMER, body))

    doc.build(elements)
    return buf.getvalue()


def _styled_table(rows: list[list[str]]) -> Table:
    table = Table(rows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.whitesmoke, colors.white]),
    ]))
    return table
