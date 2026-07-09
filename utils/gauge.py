import plotly.graph_objects as go


def render_risk_gauge(risk_percent: float, subtitle: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_percent,
            number={"suffix": "%", "font": {"color": "#1A1A2E"}},
            title={"text": subtitle, "font": {"color": "#1A1A2E"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#1A1A2E", "tickfont": {"color": "#1A1A2E"}},
                "bar": {"color": "#4a3aa7"},
                "steps": [
                    {"range": [0, 30], "color": "#e5f6e5"},
                    {"range": [30, 60], "color": "#fff4e0"},
                    {"range": [60, 100], "color": "#fbe4e4"},
                ],
            },
        )
    )
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1A1A2E"),
    )
    return fig
