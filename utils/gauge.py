import plotly.graph_objects as go

_GREEN = "#e5f6e5"
_YELLOW = "#fff4e0"
_RED = "#fbe4e4"
_NEUTRAL = "#f0f0f0"


def _high_risk_midpoint(high_risk_threshold: float) -> float:
    return high_risk_threshold + (100 - high_risk_threshold) / 2


def scaled_red_zone_start(high_risk_threshold: float, max_reachable_risk: float) -> float:
    """Midpoint between the decision threshold and the model's actual
    reachable ceiling, instead of the generic (100 - threshold) midpoint.
    Some models (e.g. lifestyle) can never get anywhere near 100% due to
    calibration on a rare-positive-class training set -- anchoring to the
    real ceiling keeps yellow AND red both genuinely reachable, instead of
    red being a decorative band nothing ever renders in.
    """
    return high_risk_threshold + (max_reachable_risk - high_risk_threshold) / 2


def _finalize(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        height=280,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1A1A2E"),
    )
    return fig


def render_risk_gauge(
    risk_percent: float,
    subtitle: str,
    high_risk_threshold: float,
    red_zone_start: float | None = None,
) -> go.Figure:
    """Gauge for models with a single binary decision threshold (lifestyle,
    cognitive). Zone boundaries are pinned to that model's own
    high_risk_threshold (percent, 0-100) rather than a fixed split, so
    "Low Risk" always renders green and "High Risk" is never green --
    otherwise a rare-positive-class model with a low tuned threshold (e.g.
    ~5%) can be labeled High Risk while still landing in a fixed 0-30%
    "green" band, which reads as a direct contradiction to users.

    red_zone_start overrides where yellow ends and red begins (see
    scaled_red_zone_start) -- pass it for models whose reachable ceiling is
    well under 100%, so red stays a genuinely reachable zone rather than a
    band nothing ever renders in.
    """
    midpoint = red_zone_start if red_zone_start is not None else _high_risk_midpoint(high_risk_threshold)
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
                    {"range": [0, high_risk_threshold], "color": _GREEN},
                    {"range": [high_risk_threshold, midpoint], "color": _YELLOW},
                    {"range": [midpoint, 100], "color": _RED},
                ],
            },
        )
    )
    return _finalize(fig)


def threshold_gauge_legend(high_risk_threshold: float, red_zone_start: float | None = None) -> str:
    midpoint = red_zone_start if red_zone_start is not None else _high_risk_midpoint(high_risk_threshold)
    return (
        f"0–{high_risk_threshold:.1f}%: Lower risk (green)  ·  "
        f"{high_risk_threshold:.1f}–{midpoint:.1f}%: High risk, borderline (yellow)  ·  "
        f"{midpoint:.1f}–100%: High risk, elevated (red)"
    )


def render_class_gauge(risk_percent: float, subtitle: str, color: str) -> go.Figure:
    """Gauge for the 3-class clinical model (Nondemented/Demented/Converted).
    There's no single threshold to anchor percentage zones to -- the label
    comes from argmax over 3 classes, which doesn't always agree with which
    side of any fixed percentage split the aggregate risk number falls on.
    Coloring the bar by the predicted class instead (reusing the same
    STRUCTURAL_LABEL_COLORS used for the result badge and cohort chart)
    keeps the gauge visually consistent with the label by construction.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_percent,
            number={"suffix": "%", "font": {"color": "#1A1A2E"}},
            title={"text": subtitle, "font": {"color": "#1A1A2E"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#1A1A2E", "tickfont": {"color": "#1A1A2E"}},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 100], "color": _NEUTRAL},
                ],
            },
        )
    )
    return _finalize(fig)


CLASS_GAUGE_LEGEND = (
    "Gauge color reflects the model's predicted class -- Nondemented (green), "
    "Converted (amber), Demented (red) -- not a percentage zone, since this "
    "model chooses among three categories rather than crossing a single risk "
    "threshold."
)
