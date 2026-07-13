from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.db import HIGH_RISK_LABELS, LOW_RISK_LABELS, display_id, fetch_all_patients
from utils.layout import render_footer

# Status palette (fixed, never themed) + validated categorical/sequential steps.
COLOR_GOOD = "#1E7A4C"
COLOR_CRITICAL = "#B33A3A"
COLOR_MUTED = "#8B94A3"
COLOR_CATEGORICAL_1 = "#2E6DA4"
COLOR_CATEGORICAL_2 = "#B8892B"
AGE_ORDINAL_RAMP = ["#C2D4E3", "#9FBAD3", "#7CA0C3", "#5686AA", "#355F82", "#1C3D5A"]
GRIDLINE = "#D5DCE3"
AXIS_INK = "#13203A"

df = fetch_all_patients()

total_patients = len(df)
high_risk = int(df["prediction_label"].isin(HIGH_RISK_LABELS).sum()) if total_patients else 0
low_risk = int(df["prediction_label"].isin(LOW_RISK_LABELS).sum()) if total_patients else 0
pending = int(df["prediction_label"].isna().sum()) if total_patients else 0
average_age = round(df["age"].mean(), 1) if total_patients else 0
confidence_values = df["confidence"].dropna() if total_patients else []
average_confidence = round(confidence_values.mean(), 1) if len(confidence_values) else 0

today = date.today()
if total_patients:
    reg_dates = pd.to_datetime(df["registration_date"], errors="coerce").dt.date
    new_this_week = int(((reg_dates >= today - timedelta(days=7)) & (reg_dates <= today)).sum())
    new_prior_week = int(
        ((reg_dates >= today - timedelta(days=14)) & (reg_dates < today - timedelta(days=7))).sum()
    )
else:
    new_this_week = 0
    new_prior_week = 0


def _bar_figure(categories, values, colors, y_title="Patients"):
    fig = go.Figure(
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            marker_line_width=0,
        )
    )
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
        yaxis=dict(
            title=dict(text=y_title, font=dict(color=AXIS_INK)),
            gridcolor=GRIDLINE,
            tickfont=dict(color=AXIS_INK, size=13),
            automargin=True,
        ),
        xaxis=dict(tickfont=dict(color=AXIS_INK, size=13), automargin=True),
        font=dict(color=AXIS_INK),
    )
    return fig


st.markdown("<div class='bg-title'>BrainGuard AI</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='bg-subtitle'>AI-Powered Dementia Risk Assessment &amp; Patient Management System</div>",
    unsafe_allow_html=True,
)

st.success("Early Detection Supports Better Outcomes")

st.write(
    "Welcome to **BrainGuard AI**. This application helps clinicians and researchers "
    "register patients, assess dementia risk using explainable AI, manage patient "
    "records, and generate professional reports."
)

st.markdown("---")

st.markdown("<div class='bg-section'>Dashboard Analytics</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Patients", total_patients)
with c2:
    st.metric("High Risk", high_risk)
with c3:
    st.metric("Low Risk", low_risk)
with c4:
    st.metric("New This Week", new_this_week, delta=new_this_week - new_prior_week)

c5, c6, c7 = st.columns(3)
with c5:
    st.metric("Pending", pending)
with c6:
    st.metric("Average Age", average_age)
with c7:
    st.metric("Avg Prediction Probability", f"{average_confidence}%")

st.markdown("---")

left, right = st.columns(2)

with left:
    st.subheader("Risk Distribution")
    st.plotly_chart(
        _bar_figure(
            ["Low Risk", "High Risk", "Pending"],
            [low_risk, high_risk, pending],
            [COLOR_GOOD, COLOR_CRITICAL, COLOR_MUTED],
        ),
        width="stretch",
        theme=None,
    )

with right:
    st.subheader("Gender Distribution")
    if total_patients:
        gender_counts = df["gender"].fillna("Unknown").value_counts()
        st.plotly_chart(
            _bar_figure(
                list(gender_counts.index),
                list(gender_counts.values),
                [COLOR_CATEGORICAL_1, COLOR_CATEGORICAL_2, COLOR_MUTED][: len(gender_counts)],
            ),
            width="stretch",
            theme=None,
        )
    else:
        st.info("No patient data available.")

st.markdown("")

if total_patients:
    st.subheader("Age Distribution")
    age_bins = ["0-20", "21-30", "31-40", "41-50", "51-60", "60+"]
    age_counts = (
        pd.cut(df["age"], bins=[0, 20, 30, 40, 50, 60, 120], labels=age_bins)
        .value_counts()
        .reindex(age_bins, fill_value=0)
    )
    st.plotly_chart(
        _bar_figure(age_bins, list(age_counts.values), AGE_ORDINAL_RAMP),
        width="stretch",
        theme=None,
    )

st.markdown("---")

st.markdown("<div class='bg-section'>Recent Patients</div>", unsafe_allow_html=True)

if total_patients == 0:
    st.info("No patients have been registered yet.")
else:
    recent = df.sort_values(by="registration_date", ascending=False).copy()
    recent["Patient ID"] = recent["id"].apply(display_id)
    display_df = recent[["Patient ID", "full_name", "gender", "age", "prediction_label", "confidence"]].rename(
        columns={"full_name": "Name", "gender": "Gender", "age": "Age",
                 "prediction_label": "Prediction", "confidence": "Prediction Probability"}
    )
    st.dataframe(display_df.head(10), width="stretch", hide_index=True)

st.markdown("---")

st.markdown("<div class='bg-section'>Brain Health Tips</div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    st.success(
        "Eat a balanced, brain-healthy diet\n\n"
        "Exercise at least 30 minutes daily\n\n"
        "Keep the mind active (puzzles, reading, learning)\n\n"
        "Sleep 7-8 hours every night\n\n"
        "Maintain a healthy body weight"
    )
with right:
    st.success(
        "Avoid smoking\n\n"
        "Limit alcohol consumption\n\n"
        "Reduce stress\n\n"
        "Monitor blood pressure\n\n"
        "Get regular cognitive check-ups"
    )

st.markdown("---")

st.markdown("<div class='bg-section'>Health Notice</div>", unsafe_allow_html=True)
st.warning(
    "BrainGuard AI is an Artificial Intelligence based decision support system.\n\n"
    "The prediction generated by this application **is not a final medical diagnosis.**\n\n"
    "Always consult a qualified neurologist before making medical decisions."
)

render_footer()
