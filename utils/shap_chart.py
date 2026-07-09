import pandas as pd
import plotly.graph_objects as go

COLOR_INCREASE = "#d03b3b"
COLOR_DECREASE = "#098009"


def render_shap_breakdown(importance: pd.DataFrame, top_n: int = 5) -> go.Figure:
    """Horizontal diverging bar chart of the top SHAP feature contributions.

    `importance` must have columns: feature, value, impact (sorted by
    absolute impact, as produced by src.predict.predict_patient).
    """
    top = importance.head(top_n).iloc[::-1]

    colors = [COLOR_INCREASE if v > 0 else COLOR_DECREASE for v in top["impact"]]
    labels = [f"{feat} = {val:.2f}" for feat, val in zip(top["feature"], top["value"])]

    fig = go.Figure(
        go.Bar(
            x=top["impact"],
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.3f}" for v in top["impact"]],
            textposition="outside",
            cliponaxis=False,
        )
    )

    fig.add_vline(x=0, line_color="#999999", line_width=1)

    fig.update_layout(
        title="Top factors driving this prediction",
        xaxis_title="SHAP impact on risk (negative = lowers risk, positive = raises risk)",
        height=140 + 40 * len(top),
        margin=dict(l=10, r=80, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1A1A2E"),
        showlegend=False,
        yaxis=dict(automargin=True),
        xaxis=dict(automargin=True),
    )

    return fig
