import streamlit as st

_CSS = """
<style>
:root {
    --brand: #4a3aa7;
    --brand-hover: #3a2d86;
    --brand-blue: #1c68c4;
    --brand-blue-hover: #15559f;
    --brand-yellow: #F0A500;
    --bg-page: #F5F5F7;
    --bg-card: #FFFFFF;
    --bg-muted: #F5F5F7;
    --border: rgba(0,0,0,0.12);
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.10);
    --ink-primary: #000000;
    --ink-secondary: #3D3D42;
    --ink-muted: #63636B;
    --good: #098009;
    --critical: #d03b3b;
    --radius-lg: 14px;
    --radius-md: 8px;
    --radius-sm: 6px;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

.stApp {
    background: var(--bg-page);
    color: var(--ink-primary);
}

.stApp, .stApp p, .stApp span, .stApp label,
.stApp li, .stApp div[data-testid="stMarkdownContainer"] {
    color: var(--ink-primary);
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: var(--ink-primary);
}

.block-container {
    padding-top: 2.5rem;
    padding-left: 3rem;
    padding-right: 3rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-card);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * {
    color: var(--ink-primary);
}

/* Typography */
.bg-title {
    text-align: left;
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--ink-primary);
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
}

.bg-subtitle {
    text-align: left;
    font-size: 15px;
    color: var(--ink-secondary);
    margin-bottom: 8px;
}

.bg-section {
    font-size: 19px;
    font-weight: 700;
    color: var(--ink-primary);
    margin-top: 20px;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
}

.bg-footer {
    text-align: center;
    font-size: 13px;
    color: var(--ink-muted);
    margin-top: 40px;
}

.bg-footer h3 {
    font-size: 15px;
    font-weight: 700;
    color: var(--brand);
}

/* Buttons */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    width: 100%;
    height: 42px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    background: var(--brand);
    color: white;
    border: none;
    transition: background 0.15s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: var(--brand-hover);
    color: white;
}

.stButton > button p, .stButton > button span, .stButton > button div,
.stDownloadButton > button p, .stDownloadButton > button span, .stDownloadButton > button div,
.stFormSubmitButton > button p, .stFormSubmitButton > button span, .stFormSubmitButton > button div {
    color: white !important;
}

.stButton > button:focus-visible {
    outline: 2px solid var(--brand);
    outline-offset: 2px;
}

/* Bordered containers (st.container(border=True)) read as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card);
    border-radius: var(--radius-lg) !important;
    border-color: var(--border) !important;
    box-shadow: var(--shadow-sm);
}

/* Metrics as stat cards */
div[data-testid="stMetric"] {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
    color: var(--ink-muted) !important;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.03em;
}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
    color: var(--ink-primary) !important;
    font-weight: 700;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    color: var(--ink-secondary);
}
.stTabs [aria-selected="true"] {
    color: var(--brand) !important;
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--brand) !important;
}

/* Dataframes */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
}

/* Status badge (risk labels) */
.risk-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: white !important;
}

/* Starting-screen role cards: white outline buttons for max contrast
   against the card, instead of a filled button blending into the page */
.st-key-patient_cta button, .st-key-clinic_cta button {
    background: white;
    border: 2px solid var(--brand);
}
.st-key-patient_cta button p, .st-key-patient_cta button span, .st-key-patient_cta button div,
.st-key-clinic_cta button p, .st-key-clinic_cta button span, .st-key-clinic_cta button div {
    color: var(--brand) !important;
}
.st-key-patient_cta button:hover, .st-key-clinic_cta button:hover {
    background: var(--brand);
}
.st-key-patient_cta button:hover p, .st-key-patient_cta button:hover span, .st-key-patient_cta button:hover div,
.st-key-clinic_cta button:hover p, .st-key-clinic_cta button:hover span, .st-key-clinic_cta button:hover div {
    color: white !important;
}

.accent-bar {
    display: block;
    height: 4px;
    width: 48px;
    border-radius: 999px;
    margin-bottom: 12px;
}
.accent-bar-blue { background: var(--brand-blue); }
.accent-bar-violet { background: var(--brand); }

.tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    margin: 4px 0 8px 0;
}
.tag-yellow {
    background: var(--brand-yellow);
    color: #000000;
}

hr {
    border-color: var(--border);
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        """
        <div class='bg-footer'>
        <hr>
        <h3>BrainGuard AI</h3>
        <p>Explainable AI Dementia Risk Assessment &amp; Patient Management System</p>
        <p>This tool supports clinical judgment; it is not a diagnosis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
