"""
Lloyd's-formatted basis risk report PDF. Institutional layout, not a screenshot.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from gad.engine.models import BasisRiskReport, TriggerDef

NAVY = colors.HexColor("#0a1628")
TEAL = colors.HexColor("#00a8a8")
SLATE = colors.HexColor("#374151")
MUTED = colors.HexColor("#6b7280")
LIGHT_BG = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#e2e8f0")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")
WHITE = colors.white
BLACK = colors.black
FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_MONO = "Courier"


def _build_page_template(canvas_obj, doc, trigger: TriggerDef, report: BasisRiskReport):
    w, h = A4
    canvas_obj.saveState()
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, h - 18 * mm, w, 18 * mm, fill=1, stroke=0)
    canvas_obj.setFillColor(TEAL)
    canvas_obj.setFont(FONT_BOLD, 11)
    canvas_obj.drawString(20 * mm, h - 12 * mm, "GAD")
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont(FONT_BODY, 9)
    canvas_obj.drawString(34 * mm, h - 12 * mm, "Parametric Trigger Basis Risk Report")
    canvas_obj.setFont(FONT_BODY, 8)
    canvas_obj.setFillColor(colors.HexColor("#94a3b8"))
    name_str = trigger.name[:50] + "..." if len(trigger.name) > 50 else trigger.name
    canvas_obj.drawRightString(w - 20 * mm, h - 12 * mm, name_str)
    canvas_obj.setStrokeColor(BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.setFont(FONT_BODY, 7)
    canvas_obj.drawString(20 * mm, 9 * mm, "oracle.gad.dev")
    canvas_obj.drawCentredString(w / 2, 9 * mm, f"Report {report.report_id}")
    canvas_obj.drawRightString(w - 20 * mm, 9 * mm, f"Page {canvas_obj.getPageNumber()}")
    canvas_obj.restoreState()


def _rho_color(rho: float) -> colors.Color:
    if rho >= 0.7:
        return GREEN
    if rho >= 0.4:
        return AMBER
    return RED


def _pct(v: float) -> str:
    return f"{v:.1%}"


def _rho_label(rho: float) -> str:
    if rho >= 0.7:
        return "Strong"
    if rho >= 0.4:
        return "Moderate"
    return "Weak"


def _styles():
    return {
        "section_label": ParagraphStyle(
            "section_label",
            fontName=FONT_BOLD,
            fontSize=7,
            textColor=TEAL,
            spaceAfter=3,
            leading=10,
            textTransform="uppercase",
            letterSpacing=1.2,
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName=FONT_BOLD,
            fontSize=18,
            textColor=NAVY,
            spaceAfter=4,
            leading=22,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName=FONT_BOLD,
            fontSize=12,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=4,
            leading=16,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=FONT_BODY,
            fontSize=9,
            textColor=SLATE,
            leading=14,
            spaceAfter=6,
        ),
        "body_muted": ParagraphStyle(
            "body_muted",
            fontName=FONT_BODY,
            fontSize=8,
            textColor=MUTED,
            leading=12,
            spaceAfter=4,
        ),
        "mono": ParagraphStyle(
            "mono",
            fontName=FONT_MONO,
            fontSize=8,
            textColor=SLATE,
            leading=12,
            spaceAfter=4,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName=FONT_BOLD,
            fontSize=8,
            textColor=WHITE,
            leading=11,
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName=FONT_BODY,
            fontSize=8,
            textColor=SLATE,
            leading=11,
        ),
    }


def _score_card_table(report: BasisRiskReport, styles: dict) -> Table:
    rho_col = _rho_color(report.spearman_rho)
    rho_label = _rho_label(report.spearman_rho)
    lloyds_pct = int(report.lloyds_score * 10)
    lloyds_col = (
        GREEN
        if report.lloyds_score >= 0.7
        else (AMBER if report.lloyds_score >= 0.5 else RED)
    )
    hex_rho = rho_col.hexval()[1:] if hasattr(rho_col, "hexval") else "059669"
    hex_lloyds = lloyds_col.hexval()[1:] if hasattr(lloyds_col, "hexval") else "059669"
    ci_str = f"95% CI  [{report.spearman_ci_lower:.2f}, {report.spearman_ci_upper:.2f}]"
    data = [
        [
            Paragraph("Spearman rho", ParagraphStyle("ml", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10)),
            Paragraph(
                f'<font color="#{hex_rho}" size="22"><b>{report.spearman_rho:.2f}</b></font>',
                ParagraphStyle("mv", fontName=FONT_BOLD, fontSize=22, textColor=rho_col, leading=26),
            ),
            Paragraph(
                f"{rho_label}  p={report.p_value:.3f}",
                ParagraphStyle("ms", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10),
            ),
        ],
        [
            Paragraph("Lloyd's alignment", ParagraphStyle("ml", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10)),
            Paragraph(
                f'<font color="#{hex_lloyds}" size="22"><b>{lloyds_pct}/10</b></font>',
                ParagraphStyle("mv", fontName=FONT_BOLD, fontSize=22, textColor=lloyds_col, leading=26),
            ),
            Paragraph(
                f"{report.lloyds_score:.0%} of criteria passing",
                ParagraphStyle("ms", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10),
            ),
        ],
        [
            Paragraph("Backtest periods", ParagraphStyle("ml", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10)),
            Paragraph(
                str(report.backtest_periods),
                ParagraphStyle("mv", fontName=FONT_BOLD, fontSize=22, textColor=NAVY, leading=26),
            ),
            Paragraph(ci_str, ParagraphStyle("ms", fontName=FONT_BODY, fontSize=7, textColor=MUTED, leading=10)),
        ],
    ]
    col_w = 57 * mm
    t = Table(data, colWidths=[col_w, col_w, col_w])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, BORDER),
                ("LINEBEFORE", (2, 0), (2, -1), 0.5, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def _lloyds_table(lloyds_detail: dict, styles: dict) -> Table:
    header = [
        Paragraph("Criterion", styles["table_header"]),
        Paragraph("Result", styles["table_header"]),
        Paragraph("Detail", styles["table_header"]),
    ]
    rows = [header]
    for criterion, result in lloyds_detail.items():
        passed = result.get("pass")
        if passed is True:
            badge = Paragraph('<font color="#059669"><b>PASS</b></font>', styles["table_cell"])
        elif passed is False:
            badge = Paragraph('<font color="#dc2626"><b>FAIL</b></font>', styles["table_cell"])
        else:
            badge = Paragraph('<font color="#d97706"><b>N/A</b></font>', styles["table_cell"])
        rows.append(
            [
                Paragraph(criterion.replace("_", " ").title(), styles["table_cell"]),
                badge,
                Paragraph(result.get("reason", ""), styles["table_cell"]),
            ]
        )
    t = Table(rows, colWidths=[55 * mm, 22 * mm, 94 * mm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, (_, result) in enumerate(lloyds_detail.items(), start=1):
        if result.get("pass") is False:
            style_cmds.append(("LINEBEFORE", (0, i), (0, i), 3, RED))
    t.setStyle(TableStyle(style_cmds))
    return t


def _confusion_matrix(report: BasisRiskReport, styles: dict) -> Table:
    fpr = report.false_positive_rate
    fnr = report.false_negative_rate
    tpr = 1 - fnr
    tnr = 1 - fpr

    def cell(label: str, value: float, value_color: colors.Color) -> Paragraph:
        h = value_color.hexval()[1:] if hasattr(value_color, "hexval") else "059669"
        return Paragraph(
            f"<b>{label}</b><br/>"
            f'<font color="#{h}" size="14"><b>{_pct(value)}</b></font>',
            ParagraphStyle(
                "cm",
                fontName=FONT_BODY,
                fontSize=8,
                textColor=SLATE,
                leading=16,
                alignment=TA_CENTER,
            ),
        )

    data = [
        [
            "",
            Paragraph("<b>Loss occurred</b>", styles["table_cell"]),
            Paragraph("<b>No loss</b>", styles["table_cell"]),
        ],
        [
            Paragraph("<b>Trigger fired</b>", styles["table_cell"]),
            cell("True positive", tpr, GREEN),
            cell("False positive", fpr, RED),
        ],
        [
            Paragraph("<b>No trigger</b>", styles["table_cell"]),
            cell("False negative", fnr, AMBER),
            cell("True negative", tnr, GREEN),
        ],
    ]
    t = Table(data, colWidths=[40 * mm, 60 * mm, 60 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#d1fae5")),
                ("BACKGROUND", (2, 1), (2, 1), colors.HexColor("#fee2e2")),
                ("BACKGROUND", (1, 2), (1, 2), colors.HexColor("#fef3c7")),
                ("BACKGROUND", (2, 2), (2, 2), colors.HexColor("#d1fae5")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return t


def generate_lloyds_report(trigger: TriggerDef, report: BasisRiskReport) -> bytes:
    """
    Lloyd's-formatted basis risk report as PDF bytes.
    Returns bytes suitable for HTTP response or file write.
    """
    buf = io.BytesIO()
    s = _styles()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=24 * mm,
        bottomMargin=22 * mm,
        title=f"GAD Basis Risk Report — {trigger.name}",
        author="GAD / OrbitCover",
        subject="Parametric Trigger Basis Risk Assessment",
    )

    def page_template(c, d):
        _build_page_template(c, d, trigger, report)

    story = []
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Parametric Trigger", s["section_label"]))
    story.append(Paragraph("Basis Risk Assessment", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

    gad_ver = getattr(report, "gad_version", None) or "—"
    meta_data = [
        ["Trigger name", trigger.name],
        ["Peril type", trigger.peril.replace("_", " ").title()],
        ["Threshold", f"{trigger.threshold} {trigger.threshold_unit}"],
        ["Data source", trigger.provenance.primary_source],
        ["Geography", str(trigger.geography)],
        ["Trigger ID", str(trigger.trigger_id)],
        ["Report ID", str(report.report_id)],
        ["Computed at", report.computed_at.strftime("%Y-%m-%d %H:%M UTC")],
        ["GAD version", gad_ver],
    ]
    meta_table = Table(
        [[Paragraph(k, s["body_muted"]), Paragraph(str(v), s["mono"])] for k, v in meta_data],
        colWidths=[50 * mm, 121 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Summary scores", s["section_label"]))
    story.append(_score_card_table(report, s))
    story.append(Spacer(1, 8 * mm))
    rho = report.spearman_rho
    verdict_text = (
        f"This trigger demonstrates <b>{_rho_label(rho).lower()} basis risk alignment</b> "
        f"(rho = {rho:.2f}) with a Lloyd's alignment score of "
        f"{report.lloyds_score:.0%} ({int(report.lloyds_score * 10)}/10 criteria passing). "
    )
    if rho >= 0.7 and report.lloyds_score >= 0.7:
        verdict_text += "The trigger is suitable for Lloyd's parametric product submission."
    elif rho >= 0.4:
        verdict_text += (
            "The trigger may require threshold adjustment or an alternative "
            "data source before Lloyd's submission."
        )
    else:
        verdict_text += (
            "The trigger has material basis risk. Redesign is recommended "
            "before advancing to underwriting."
        )
    story.append(Paragraph(verdict_text, s["body"]))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("Lloyd's alignment checklist", s["h2"]))
    story.append(
        Paragraph(
            "Each criterion maps to Lloyd's standards for parametric product approval. "
            "Failed criteria (red border) require remediation before submission.",
            s["body_muted"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(_lloyds_table(report.lloyds_detail, s))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Performance matrix", s["h2"]))
    story.append(
        Paragraph(
            "Trigger performance against historical loss events. False positive rate "
            "and false negative rate are the primary basis risk indicators for reinsurance pricing.",
            s["body_muted"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(_confusion_matrix(report, s))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Data source provenance", s["h2"]))
    prov = trigger.provenance
    backtest_start = report.backtest_start
    backtest_end = report.backtest_end_inclusive
    if hasattr(backtest_start, "strftime"):
        start_str = backtest_start.strftime("%Y-%m-%d")
    else:
        start_str = str(backtest_start)
    if hasattr(backtest_end, "strftime"):
        end_str = backtest_end.strftime("%Y-%m-%d")
    else:
        end_str = str(backtest_end)
    prov_data = [
        ["Primary source", prov.primary_source],
        ["Source URL", prov.primary_url],
        ["Fallback source", prov.fallback_source or "None specified"],
        ["Max data latency", f"{prov.max_data_latency_seconds}s"],
        ["Historical depth", f"{prov.historical_years_available} years"],
        ["Backtest range", f"{start_str} to {end_str}"],
        ["Periods analysed", str(report.backtest_periods)],
    ]
    prov_table = Table(
        [[Paragraph(k, s["body_muted"]), Paragraph(str(v), s["mono"])] for k, v in prov_data],
        colWidths=[55 * mm, 116 * mm],
    )
    prov_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(prov_table)
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(
        Paragraph(
            "This report was generated by GAD (Get Actuary Done), open-source parametric "
            "insurance infrastructure by OrbitCover. The computation engine is published "
            "under AGPL-3.0. The trigger schema specification is published under MIT.",
            s["body_muted"],
        )
    )
    doc.build(story, onFirstPage=page_template, onLaterPages=page_template)
    return buf.getvalue()
