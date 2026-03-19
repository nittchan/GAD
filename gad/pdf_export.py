"""
PDF export for basis risk reports (Phase 2).
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from gad._models_legacy import BasisRiskReport, TriggerDef


def build_pdf(report: BasisRiskReport, trigger: TriggerDef) -> bytes:
    """Produce a one-shot PDF report (trigger + score card + confusion + Lloyd's)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GADTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "GADH2",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=4,
    )
    body = styles["Normal"]

    story = []
    story.append(Paragraph("GAD — Basis Risk Report", title_style))
    story.append(Paragraph(f"<b>{report.trigger_name}</b> ({report.trigger_id})", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Trigger definition", h2_style))
    trig_data = [
        ["Peril", trigger.peril.value],
        ["Variable", trigger.variable],
        ["Location", f"lat={trigger.location.lat}, lon={trigger.location.lon}"],
        ["Threshold", f"{trigger.trigger_logic.kind.value} {trigger.trigger_logic.threshold}"],
        ["Date range", f"{trigger.date_range.start} to {trigger.date_range.end}"],
        ["Payout", trigger.payout_formula_summary[:80] + ("..." if len(trigger.payout_formula_summary) > 80 else "")],
    ]
    if trigger.bounding_box:
        trig_data.append([
            "Bounding box",
            f"[{trigger.bounding_box.min_lat}, {trigger.bounding_box.max_lat}] × [{trigger.bounding_box.min_lon}, {trigger.bounding_box.max_lon}]",
        ])
    t = Table(trig_data, colWidths=[1.2 * inch, 5 * inch])
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(t)
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Score card", h2_style))
    story.append(Paragraph(
        f"Headline Spearman ρ = {report.headline_rho:.3f} (95% CI [{report.headline_ci_low:.3f}, {report.headline_ci_high:.3f}], "
        f"p-value = {report.headline_p_value:.4g}). Lloyd's pass rate: {report.lloyds.passed_count}/{report.lloyds.total_count}.",
        body,
    ))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Confusion matrix (period-level)", h2_style))
    c = report.backtest.confusion
    conf_data = [
        ["", "Loss no", "Loss yes"],
        ["Trigger no", str(c.true_negative), str(c.false_negative)],
        ["Trigger yes", str(c.false_positive), str(c.true_positive)],
    ]
    tc = Table(conf_data, colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch])
    tc.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(tc)
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Lloyd's checklist", h2_style))
    lloyd_data = [["Criterion", "Pass", "Explanation"]]
    for x in report.lloyds.criteria:
        lloyd_data.append([f"{x.criterion_id} {x.name}", "Yes" if x.passed else "No", x.explanation[:60] + ("..." if len(x.explanation) > 60 else "")])
    tl = Table(lloyd_data, colWidths=[1.8 * inch, 0.5 * inch, 3.7 * inch])
    tl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(tl)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(
        "Methodology: Spatial basis risk and loss-proxy Spearman rank correlation; back-test vs open-data loss proxy. "
        "Lloyd's checklist is Phase-1 underwriting-style gates, not a substitute for formal filing.",
        ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey),
    ))

    doc.build(story)
    return buf.getvalue()
