import plotly.graph_objects as go

_GREEN = "#E2EFE7"
_YELLOW = "#F3E9D6"
_RED = "#F5E1E1"
_NEUTRAL = "#EDF1F5"
_INK = "#13203A"
_BAR = "#1C3D5A"


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
        font=dict(color=_INK),
    )
    return fig


def render_risk_gauge(
    risk_percent: float,
    subtitle: str,
    high_risk_threshold: float,
    red_zone_start: float | None = None,
    axis_max: float = 100.0,
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

    axis_max caps the dial's top. On a full 0-100 axis, a model that can
    only reach ~30% paints ~70% of the arc red, so even a genuinely low
    result looks alarming. Passing a cap near the model's reachable ceiling
    makes the green/yellow/red bands proportionate to what the model can
    actually output, so a low result reads as mostly green.
    """
    midpoint = red_zone_start if red_zone_start is not None else _high_risk_midpoint(high_risk_threshold)
    top = max(axis_max, risk_percent, midpoint)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=risk_percent,
            number={"suffix": "%", "font": {"color": _INK}},
            title={"text": subtitle, "font": {"color": _INK}},
            gauge={
                "axis": {"range": [0, top], "tickcolor": _INK, "tickfont": {"color": _INK}},
                "bar": {"color": _BAR},
                "steps": [
                    {"range": [0, high_risk_threshold], "color": _GREEN},
                    {"range": [high_risk_threshold, midpoint], "color": _YELLOW},
                    {"range": [midpoint, top], "color": _RED},
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
            number={"suffix": "%", "font": {"color": _INK}},
            title={"text": subtitle, "font": {"color": _INK}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": _INK, "tickfont": {"color": _INK}},
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
