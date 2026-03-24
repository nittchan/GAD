"""Confusion matrix heatmap (TP/FP/FN/TN) — parchment theme."""

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
            colorscale=[[0, "#EDE7E0"], [1, "#2E8B6F"]],
            showscale=False,
            text=[[str(tn), str(fp)], [str(fn), str(tp)]],
            texttemplate="%{text}",
            textfont={"color": "#1E1B18", "size": 14, "family": "JetBrains Mono, ui-monospace, monospace"},
        )
    )
    fig.update_layout(
        paper_bgcolor="#F5F0EB",
        plot_bgcolor="#F5F0EB",
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text="Confusion (period-level)", font=dict(family="Instrument Sans, sans-serif", size=14, color="#1E1B18")),
        font=dict(family="Instrument Sans, sans-serif", color="#7A7267"),
        height=280,
    )
    fig.update_xaxes(tickfont=dict(family="JetBrains Mono, monospace", size=12))
    fig.update_yaxes(tickfont=dict(family="JetBrains Mono, monospace", size=12))
    return fig


def confusion_matrix_markdown(report: BasisRiskReport) -> str:
    rows = report.backtest_rows or []
    total = len(rows)
    if total == 0:
        return "| | Loss occurred | No loss |\n|---|---|---|\n| Trigger fired | TP: 0.0% | FP: 0.0% |\n| No trigger | FN: 0.0% | TN: 0.0% |"

    tp, fp, fn, tn = _confusion_from_report(report)
    tpr = tp / total
    fpr = fp / total
    fnr = fn / total
    tnr = tn / total
    return (
        f"| | Loss occurred | No loss |\n"
        f"|---|---|---|\n"
        f"| Trigger fired | TP: {tpr:.1%} | FP: {fpr:.1%} |\n"
        f"| No trigger | FN: {fnr:.1%} | TN: {tnr:.1%} |"
    )
