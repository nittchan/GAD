"""Confusion matrix heatmap (TP/FP/FN/TN)."""

from __future__ import annotations

import plotly.graph_objects as go

from gad.engine.models import BasisRiskReport


def _confusion_from_report(report: BasisRiskReport) -> tuple[int, int, int, int]:
    rows = report.backtest_rows or []
    tp = fp = fn = tn = 0
    for r in rows:
        if r.trigger_fired and r.loss_occurred:
            tp += 1
        elif r.trigger_fired and not r.loss_occurred:
            fp += 1
        elif not r.trigger_fired and r.loss_occurred:
            fn += 1
        else:
            tn += 1
    return tp, fp, fn, tn


def confusion_matrix_fig(report: BasisRiskReport) -> go.Figure:
    tp, fp, fn, tn = _confusion_from_report(report)
    z = [[tn, fp], [fn, tp]]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["Loss no", "Loss yes"],
            y=["Trigger no", "Trigger yes"],
            colorscale=[[0, "#1f2937"], [1, "#10b981"]],
            showscale=False,
            text=[[str(tn), str(fp)], [str(fn), str(tp)]],
            texttemplate="%{text}",
            textfont={"color": "#f9fafb", "size": 14},
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a",
        margin=dict(l=40, r=20, t=40, b=40),
        title="Confusion (period-level)",
        height=280,
    )
    return fig
