"""Back-test: dual strip timeline + scatter."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from gad.engine.models import BasisRiskReport


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
        go.Bar(x=periods, y=fire, name="Trigger fired", marker_color="#00d4d4"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=loss, name="Loss event", marker_color="#a371f7"),
        row=2, col=1,
    )
    fig.add_trace(
        go.Bar(x=periods, y=mismatch, name="Mismatch", marker_color="#ef4444"),
        row=3, col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a",
        height=320,
        margin=dict(l=40, r=20, t=30, b=40),
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(range=[0, 1.05], row=1, col=1)
    fig.update_yaxes(range=[0, 1.05], row=2, col=1)
    fig.update_yaxes(range=[0, 1.05], row=3, col=1)
    return fig


def scatter_fig(report: BasisRiskReport) -> go.Figure:
    rows = report.backtest_rows or []
    x = [r.trigger_value for r in rows]
    y = [1.0 if r.loss_occurred else 0.0 for r in rows]
    colors = []
    for r in rows:
        if r.trigger_fired and r.loss_occurred:
            colors.append("#10b981")
        elif r.trigger_fired and not r.loss_occurred:
            colors.append("#ef4444")
        elif not r.trigger_fired and r.loss_occurred:
            colors.append("#f59e0b")
        else:
            colors.append("#6b7280")
    fig = go.Figure(
        go.Scatter(
            x=x, y=y, mode="markers",
            marker=dict(size=10, color=colors),
            name="periods",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a",
        height=360,
        margin=dict(l=40, r=20, t=40, b=40),
        title="Index vs loss (TP green, FP red, FN amber, TN gray)",
        xaxis_title="Trigger value",
        yaxis_title="Loss occurred",
    )
    fig.update_yaxes(range=[-0.1, 1.1])
    return fig
