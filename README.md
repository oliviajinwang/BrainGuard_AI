# BrainGuard AI

> An explainable AI-powered dementia risk assessment and clinical decision-support prototype built using machine learning, Streamlit, and XGBoost.

<p align="center">

**Live Demo:** https://brain-guard-ai.streamlit.app/

</p>

---

# Overview

BrainGuard AI is an educational and clinical decision-support prototype that estimates dementia-related risk using machine learning models trained on research datasets. The application combines **lifestyle, cognitive, and structural (MRI-derived)** information to provide explainable risk estimates and personalized recommendations for patients and clinicians.

Rather than functioning as a diagnostic tool, BrainGuard AI was designed to demonstrate how explainable artificial intelligence (XAI) can support conversations between patients and healthcare professionals by highlighting which factors contributed most strongly to each prediction.

Research suggests that approximately **40% of dementia cases may be delayed or prevented through modification of lifestyle-related risk factors**. BrainGuard AI aims to encourage those conversations by identifying potentially modifiable factors while clearly communicating the limitations of machine learning in healthcare.

---

# Disclaimer

BrainGuard AI is an educational and clinical decision-support prototype.

It is **not**:

- a diagnosis
- a certified medical device
- a replacement for professional medical evaluation

Model predictions represent statistical associations learned from limited research datasets and **do not establish causation**.

- A **Low Risk** result does not rule out dementia.
- A **High Risk** result does not mean a patient has or will develop dementia.
- "What-if" comparisons illustrate model behavior only and should not be interpreted as medical advice.

Anyone experiencing memory loss, cognitive decline, or concerns regarding dementia should consult a qualified healthcare professional.

---

# Features

## Patient Portal

- Quick lifestyle dementia risk assessment
- Patient registration
- AI-powered educational assistant
- Personalized lifestyle recommendations
- Explainable AI summaries
- Accessible interface designed for older adults

---

## Clinician Portal

- Secure clinician authentication
- Patient management dashboard
- Patient history database
- CSV patient import
- Lifestyle assessment
- Structural (MRI-derived) assessment
- SHAP explainability
- Personalized action plans
- Downloadable PDF medical reports

---

## Machine Learning

BrainGuard AI currently includes three machine learning pipelines:

| Model | Purpose |
|--------|---------|
| Lifestyle Model | Estimates dementia-related risk using modifiable lifestyle factors |
| Cognitive Model | Estimates dementia-related risk using cognitive assessment data |
| Clinical Model | Estimates dementia-related risk using structural MRI measurements |

Models are implemented using **XGBoost** and explained using **SHAP (SHapley Additive Explanations)** to provide transparent feature-level reasoning.

---

# Model Performance

BrainGuard AI uses separate models for lifestyle-based screening and clinician-facing assessment. The results below come from held-out evaluation data and should not be interpreted as clinical performance.

| Model | Assessment | Test Samples | Positive Samples | Accuracy | Precision | Recall | F1 Score | ROC-AUC | Decision Threshold |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XGBoost | Lifestyle | 360 | 16 | 73.9% | 11.8% | 75.0% | 20.3% | 0.788 | 5.01% |
| XGBoost | Clinical | 76* | 37* | 75.0% | 76.5% | 70.3% | 73.2% | 0.854 | 50.0% |

\*The clinical sample counts should be included only if the production XGBoost model was evaluated using the same 76-row test set shown for the clinical comparison models.

The lifestyle model uses a low decision threshold to prioritize identifying more potentially at-risk cases. This increases recall but also produces many false-positive results. Therefore, the lifestyle assessment is presented as a preliminary screening estimate rather than a diagnosis.

# Technology Stack

### Machine Learning

- XGBoost
- Scikit-learn
- SHAP
- pandas
- NumPy

### Frontend

- Streamlit
- Plotly
- Matplotlib

### Backend

- Python
- SQLite

### AI

- OpenAI API
- Explainable AI (SHAP)

### Reports

- FPDF2
- QRCode

---

# 📸 Application Preview

## Welcome Page

<p align="center">
<img src="assets/home.png" width="900">
</p>

---

## Patient Risk Assessment

<p align="center">
<img src="assets/patient-risk.png" width="900">
</p>

---

## Clinician Dashboard

<p align="center">
<img src="assets/clinician-dashboard.png" width="900">
</p>

---

# Repository Structure

```text
app.py                  # Application entry point
views/                  # Streamlit pages
utils/                  # Shared utilities
src/                    # Machine learning pipelines
models/                 # Saved models and SHAP explainers
data/                   # Sample datasets
tests/                  # Automated tests
assets/                 # README screenshots
.streamlit/             # Streamlit configuration
```

---

# Installation

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

Optional:

- OpenAI API Key for chatbot functionality

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# (Optional) Enable the AI assistant
export OPENAI_API_KEY=sk-...

# or

echo 'OPENAI_API_KEY = "sk-..."' > .streamlit/secrets.toml

# Launch the application
streamlit run app.py
```

The application will be available at:

```
http://localhost:8501
```

The SQLite database (`database.db`) is created automatically on first launch.

Clinicians register their own accounts—no demo credentials are included.

---

# Running Tests

```bash
pytest tests/ -v
```

The automated test suite validates:

- authentication
- machine learning predictions
- chatbot functionality
- report generation
- database operations
- application utilities

---

# Current Limitations

BrainGuard AI is intended for educational and research purposes.

Current limitations include:

- Models are trained on publicly available research datasets.
- External validation on an independent clinical cohort has not yet been completed.
- Predictions should not be interpreted as clinical diagnoses.
- Performance may vary across populations that differ from the training data.
- The application complements—rather than replaces—clinical judgment.

---

# Future Work

Planned improvements include:

- External clinical validation
- Additional MRI datasets
- Improved probability calibration
- Longitudinal patient tracking
- Expanded clinician analytics
- Enhanced explainability visualizations
- Broader accessibility support

---

# Authors

| Name | Role |
|------|------|
| **Olivia Wang** (International Community School) | Project Lead & Machine Learning |
| **David Chen** (Tabor Academy) | Backend Development |
| **Emma Liu** (Shanghai American School) | Frontend Development |
| **Yuki Mach** (International School in Hawaii) | UI/UX Design |

---

# Acknowledgments

We thank the creators of the open-source datasets and software libraries that made this educational project possible, including the developers of Streamlit, XGBoost, SHAP, scikit-learn, and the research datasets used throughout the project.

---

**BrainGuard AI is intended solely for educational and research purposes and should not be used as a substitute for professional medical advice or diagnosis.**