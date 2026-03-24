"""Back-test: dual strip timeline + scatter — parchment theme."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from gad.engine.models import BasisRiskReport

_FONT_LABEL = dict(family="Instrument Sans, sans-serif", color="#7A7267", size=12)
_FONT_TICK = dict(family="JetBrains Mono, monospace", color="#7A7267", size=11)
_BG = "#F5F0EB"


def rho_label(rho: float) -> str:
    if rho >= 0.7:
        return "Strong"
    if rho >= 0.4:
        return "Moderate"
    return "Weak"


def chart_summary(report: BasisRiskReport) -> str:
    return (
        f"Chart summary: Spearman rho = {report.spearman_rho:.2f} "
        f"({rho_label(report.spearman_rho)} correlation). "
        f"False positive rate {report.false_positive_rate:.1%}, "
        f"false negative rate {report.false_negative_rate:.1%}."
    )


def timeline_fig(report: BasisRiskReport) -> go.Figure:
    rows = report.backtest_rows or []
    periods = [r.period for r in rows]
    fire = [1 if r.trigger_fired else 0 for r in rows]
    loss = [1 if r.loss_occurred else 0 for r in rows]
    mismatch = [1 if (r.trigger_fired != r.loss_occurred) else 0 for r in rows]
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, row_heights=[0.2, 0.2, 0.2], vertical_spacing=0.08
    )
    fig.add_trace(
        go.Bar(x=periods, y=fire, name="Trigger fired", marker_color="#C8553D"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=loss, name="Loss event", marker_color="#467B6B"),
        row=2, col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=mismatch, name="Mismatch", marker_color="#A63D40"),
        row=3, col=1,
    )
    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=_FONT_LABEL,
        height=320,
        margin=dict(l=40, r=20, t=30, b=40),
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=_FONT_LABEL),
    )
    for i in range(1, 4):
        fig.update_yaxes(range=[0, 1.05], row=i, col=1, tickfont=_FONT_TICK, gridcolor="#E3DCD3")
        fig.update_xaxes(row=i, col=1, tickfont=_FONT_TICK, gridcolor="#E3DCD3")
    return fig


def scatter_fig(report: BasisRiskReport) -> go.Figure:
    rows = report.backtest_rows or []
    x = [r.trigger_value for r in rows]
    y = [1.0 if r.loss_occurred else 0.0 for r in rows]
    colors = []
    for r in rows:
        if r.trigger_fired and r.loss_occurred:
            colors.append("#2E8B6F")   # verdigris (TP)
        elif r.trigger_fired and not r.loss_occurred:
            colors.append("#A63D40")   # carmine (FP)
        elif not r.trigger_fired and r.loss_occurred:
            colors.append("#D4A017")   # amber (FN)
        else:
            colors.append("#9B9286")   # warm gray (TN)
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(size=10, color=colors),
            name="periods",
        )
    )
    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=_FONT_LABEL,
        height=360,
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text="Index vs loss (TP green, FP red, FN amber, TN gray)", font=dict(family="Instrument Sans, sans-serif", size=13, color="#7A7267")),
        xaxis_title="Trigger value",
        yaxis_title="Loss occurred",
    )
    fig.update_xaxes(tickfont=_FONT_TICK, gridcolor="#E3DCD3")
    fig.update_yaxes(range=[-0.1, 1.1], tickfont=_FONT_TICK, gridcolor="#E3DCD3")
    return fig
