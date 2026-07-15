import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
    /* BrainGuard clinical theme: intentionally warm, quiet, and high contrast. */
    --brand: #276D68;
    --brand-hover: #1E5753;
    --brand-blue: #356D8B;
    --brand-blue-hover: #285872;
    --brand-yellow: #8A5A00;
    --brand-teal-soft: #E1F0EC;
    --brand-navy: #102A43;
    --bg-page: #FCFAF6;
    --bg-card: #FFFFFF;
    --bg-muted: #F3F0E9;
    --border: #D9DED9;
    --shadow-sm: 0 1px 2px rgba(16, 42, 67, 0.07), 0 6px 16px rgba(16, 42, 67, 0.035);
    --shadow-md: 0 12px 30px rgba(16, 42, 67, 0.13);
    --ink-primary: #102A43;
    --ink-secondary: #3E5668;
    --ink-muted: #627482;
    --good: #256C4C;
    --moderate: #8A5A00;
    --critical: #A63838;
    --radius-lg: 18px;
    --radius-md: 12px;
    --radius-sm: 10px;
    --font-serif: 'Fraunces', Georgia, serif;
    --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'JetBrains Mono', 'Courier New', monospace;

    /* Restrained early-2000s accent palette -- used only for decorative
       hero/illustration elements (see views/welcome.py), never for body
       text, forms, results, or clinical data. */
    --y2k-ice: #E4F1F7;
    --y2k-ice-deep: #BFE0EC;
    --y2k-cyan: #46C7DC;
    --y2k-cyan-glow: rgba(70, 199, 220, 0.35);
    --y2k-silver: #CBD5DA;
    --y2k-silver-dark: #8FA0A8;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

.stApp {
    background: var(--bg-page);
    color: var(--ink-primary);
    font-family: var(--font-sans);
}

.stApp, .stApp p, .stApp span, .stApp label,
.stApp li, .stApp div[data-testid="stMarkdownContainer"] {
    color: var(--ink-primary);
}

.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: var(--ink-primary);
    font-family: var(--font-serif);
}

.block-container {
    padding-top: 1.75rem;
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
    font-family: var(--font-serif);
    font-size: 34px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--ink-primary);
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
}

.bg-subtitle {
    text-align: left;
    font-size: 16px;
    color: var(--ink-secondary);
    margin-bottom: 8px;
}

.bg-section {
    font-family: var(--font-serif);
    font-size: 24px;
    font-weight: 600;
    color: var(--ink-primary);
    margin-top: 20px;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.bg-footer {
    text-align: center;
    font-size: 13px;
    color: var(--ink-muted);
    margin-top: 40px;
}

.bg-footer h3 {
    font-family: var(--font-serif);
    font-size: 17px;
    font-weight: 600;
    color: var(--brand);
}

/* Buttons -- pill-shaped, matching the reference's rounded CTAs */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    width: 100%;
    min-height: 48px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    background: var(--brand);
    color: white;
    border: none;
    transition: background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: var(--brand-hover);
    color: white;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(30, 87, 83, 0.18);
}

.stButton > button:active,
.stDownloadButton > button:active,
.stFormSubmitButton > button:active {
    transform: translateY(1px);
    box-shadow: none;
}

.stButton > button p, .stButton > button span, .stButton > button div,
.stDownloadButton > button p, .stDownloadButton > button span, .stDownloadButton > button div,
.stFormSubmitButton > button p, .stFormSubmitButton > button span, .stFormSubmitButton > button div {
    color: white !important;
}

.stButton > button:focus-visible {
    outline: 3px solid var(--brand-navy);
    outline-offset: 3px;
}

/* Bordered containers (st.container(border=True)) read as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card);
    border-radius: var(--radius-lg) !important;
    border-color: var(--border) !important;
    box-shadow: var(--shadow-sm);
}

/* Form controls use enough target size and an explicit focus ring for keyboard users. */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="select"] > div {
    font-size: 16px !important;
    border-radius: 10px !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="select"] > div { min-height: 48px; }
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus-within,
div[data-baseweb="select"]:focus-within > div {
    border-color: var(--brand) !important;
    box-shadow: 0 0 0 3px rgba(39, 109, 104, 0.19) !important;
}
div[data-testid="stRadio"] label {
    min-height: 48px;
    align-items: center;
    font-size: 16px;
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
    font-family: var(--font-mono);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.04em;
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
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: white !important;
}

/* Starting-screen role cards: white outline buttons for max contrast
   against the card, instead of a filled button blending into the page */
.st-key-patient_cta button, .st-key-clinic_cta button {
    background: white;
    border: 1.5px solid var(--brand);
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
    height: 3px;
    width: 40px;
    border-radius: 999px;
    margin-bottom: 12px;
}
.accent-bar-blue { background: var(--brand-blue); }
.accent-bar-violet { background: var(--brand); }

.tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin: 4px 0 8px 0;
}
.tag-yellow {
    background: rgba(184, 137, 43, 0.14);
    color: var(--brand-yellow);
}

hr {
    border-color: var(--border);
}

/* Switch Role / Log Out: a floating pill in the bottom-right corner of
   the main content area instead of the sidebar, positioned so it never
   overlaps the Dashboard's charts (fixed, small footprint, corner only). */
.st-key-switch_role_btn { display: none; }

/* Shared app header and navigation. Streamlit buttons keep their native keyboard semantics. */
.st-key-public_header, .st-key-portal_header {
    border-bottom: 1px solid var(--border);
    margin: -1.75rem -3rem 1.5rem;
    padding: 15px 3rem;
    background: rgba(252, 250, 246, 0.96);
}
.st-key-portal_header {
    position: sticky;
    top: 0;
    z-index: 100;
}
.bg-brand { display:flex; align-items:center; color:var(--brand-navy); font-family:var(--font-serif); font-size:22px; font-weight:600; letter-spacing:-0.01em; }
/* Public pages carry a larger wordmark; the signed-in portal header keeps
   the compact size so its nav controls stay on one row. */
.st-key-public_header .bg-brand { font-size:32px; }
.bg-header-note { color:var(--ink-secondary); font-size:14px; text-align:right; }
.bg-current-page { color:var(--ink-primary); font-size:15px; font-weight:650; line-height:1.25; }
.bg-current-page span { display:block; color:var(--ink-muted); text-transform:uppercase; letter-spacing:.06em; font-family:var(--font-mono); font-size:10px; margin-bottom:3px; }
.st-key-header_switch_role button { background:var(--bg-card); color:var(--brand) !important; border:1px solid var(--brand); }
.st-key-header_switch_role button p, .st-key-header_switch_role button span, .st-key-header_switch_role button div { color:var(--brand) !important; }
.st-key-header_switch_role button:hover { background:var(--brand-teal-soft); color:var(--brand) !important; }

/* Shared information modules. */
.bg-icon { flex: 0 0 auto; }
.bg-trust-item { display:flex; gap:10px; align-items:flex-start; padding:14px 16px; border:1px solid var(--border); border-radius:var(--radius-md); background:var(--bg-card); }
.bg-trust-item .bg-icon { color:var(--brand); margin-top:2px; flex:0 0 auto; }
.bg-trust-item strong, .bg-trust-item span { display:block; }
.bg-trust-item strong { color:var(--ink-primary); font-size:14px; margin-bottom:3px; }
.bg-trust-item span { color:var(--ink-secondary); font-size:12.5px; line-height:1.4; }
.bg-step-progress { margin:0 0 22px; }
.bg-step-progress > div:first-child { display:flex; justify-content:space-between; gap:12px; color:var(--ink-secondary); font-size:15px; margin-bottom:8px; }
.bg-step-progress > div:first-child strong { color:var(--ink-primary); }
.bg-progress-track { height:10px; border-radius:999px; overflow:hidden; background:#E4E8E4; }
.bg-progress-track span { display:block; height:100%; background:var(--brand); border-radius:inherit; transition:width 300ms ease; }
.bg-status-chip { display:inline-flex; align-items:center; gap:5px; width:max-content; border-radius:999px; padding:5px 9px; font-weight:700; font-size:12px; white-space:nowrap; }
.bg-status-chip .bg-icon { width:14px; height:14px; }
.bg-status-needs-review { color:#7B2727; background:#FBE9E7; border:1px solid #E7B7B2; }
.bg-status-monitor { color:#6C4B06; background:#FFF4D6; border:1px solid #E6CD8C; }
.bg-status-stable { color:#1D5B40; background:#E7F3EB; border:1px solid #B8D7C1; }
.bg-status-pending { color:#465967; background:#EAF0F3; border:1px solid #C7D5DC; }
.bg-entry-mode-banner { display:block; padding:10px 14px; margin:0 0 16px; border-radius:var(--radius-md); background:var(--brand-teal-soft); color:var(--ink-primary); font-size:14px; border:1px solid var(--border); }
.bg-entry-mode-banner strong { color:var(--ink-primary); }

/* Role cards and question cards use stable keyed containers. */
.st-key-role_self_card, .st-key-role_caregiver_card, .st-key-role_clinic_card,
.st-key-question_card, .st-key-result_summary, .st-key-worklist_card {
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}
.st-key-role_self_card:hover, .st-key-role_caregiver_card:hover, .st-key-role_clinic_card:hover { transform:translateY(-4px); box-shadow:var(--shadow-md); border-color:#AABFBA; }
.role-card-icon { display:flex; align-items:center; justify-content:center; width:46px; height:46px; border-radius:14px; background:var(--brand-teal-soft); color:var(--brand); margin-bottom:16px; }
.role-card-icon.clinic { color:var(--brand-navy); background:#E7EEF3; }
.role-card-icon.caregiver { color:#7A5713; background:#FBF1DB; }
.role-card-kicker { color:var(--ink-muted); font-family:var(--font-mono); font-size:11px; letter-spacing:.05em; text-transform:uppercase; }
.role-card-copy { color:var(--ink-secondary); font-size:16px; min-height:50px; }
.question-help { color:var(--ink-secondary); font-size:15px; }

/* Dense clinician worklist. */
.bg-worklist-row { display:grid; grid-template-columns:1.4fr 1.1fr .9fr .95fr .95fr .9fr auto; gap:12px; align-items:center; padding:13px 0; border-bottom:1px solid var(--border); font-size:14px; }
.bg-worklist-row:last-child { border-bottom:0; }
.bg-worklist-header { color:var(--ink-muted); font-family:var(--font-mono); font-size:10px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; padding-top:0; }
.bg-worklist-name { color:var(--ink-primary); font-weight:700; }
.bg-worklist-secondary { color:var(--ink-secondary); font-size:12px; margin-top:2px; }
.bg-worklist-action .stButton > button { min-height:38px; font-size:13px; padding:4px 10px; }

@keyframes bg-fade-rise { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
.bg-enter { animation:bg-fade-rise 300ms ease-out both; }

/* Loading skeleton: shimmer placeholder bars shown instead of blank space
   while a page waits on a slow calculation (model load, worklist build). */
.bg-skeleton { display:flex; flex-direction:column; gap:10px; padding:4px 0; }
.bg-skeleton-line { height:14px; border-radius:7px; background:linear-gradient(90deg, var(--bg-muted) 25%, #EAE6DC 37%, var(--bg-muted) 63%); background-size:400% 100%; animation:bg-skeleton-shimmer 1.4s ease-in-out infinite; }
@keyframes bg-skeleton-shimmer { 0% { background-position:100% 50%; } 100% { background-position:0 50%; } }
.bg-score { color:var(--brand-navy); font-size:clamp(2.3rem,5vw,3.5rem); font-weight:750; line-height:1; letter-spacing:-.045em; font-variant-numeric:tabular-nums; }
.bg-score span { display:block; color:var(--ink-secondary); font-size:14px; font-weight:500; letter-spacing:0; margin-top:8px; }
.bg-score-enter { animation:bg-fade-rise 420ms ease-out both; }
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration:0.01ms !important; animation-iteration-count:1 !important; scroll-behavior:auto !important; transition-duration:0.01ms !important; }
}

@media (max-width: 768px) {
    .block-container { padding-left:1rem; padding-right:1rem; padding-top:1rem; }
    .st-key-public_header, .st-key-portal_header { margin:-1rem -1rem 1rem; padding:12px 1rem; }
    .st-key-portal_header [data-testid="stHorizontalBlock"] { gap:.45rem; }
    .bg-current-page { display:none; }
    .bg-header-note { font-size:12px; }
    .bg-worklist-row { grid-template-columns:1.2fr 1fr; gap:8px; padding:14px 0; }
    .bg-worklist-header { display:none; }
    .bg-worklist-row > :nth-child(4), .bg-worklist-row > :nth-child(5), .bg-worklist-row > :nth-child(6) { display:none; }
}

@media (max-width: 480px) {
    .bg-brand { font-size:17px; }
    .st-key-public_header .bg-brand { font-size:23px; }
    .st-key-portal_header [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
    .st-key-portal_header [data-testid="column"] { min-width:calc(50% - .3rem); }
    .bg-trust-item { padding:10px; }
    .bg-trust-item span { display:none; }
    .bg-step-progress > div:first-child { align-items:flex-start; flex-direction:column; gap:3px; }
}

/* Full-viewport opaque cover shown for one render pass while switching
   roles, so stale dashboard/portal content can never peek through while
   the browser prunes it. */
.st-key-switching_overlay {
    position: fixed;
    inset: 0;
    z-index: 999999;
    background: var(--bg-page);
    display: flex;
    align-items: center;
    justify-content: center;
}
.st-key-switching_overlay div[data-testid="stMarkdownContainer"] {
    display: flex;
    justify-content: center;
    width: 100%;
}
.st-key-switching_overlay p {
    font-size: 18px;
    font-weight: 600;
    color: var(--ink-secondary);
    text-align: center;
}
</style>
"""


_HIDE_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"] { display: none !important; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def hide_sidebar() -> None:
    # st.navigation(..., position="hidden") only hides the nav *links* --
    # Streamlit still allocates the sidebar's own container (white
    # background + collapse arrow), which showed up as a persistent empty
    # white block next to the Welcome/About/login screens. Call this only
    # once app.py has finished resolving st.session_state.role for the
    # current run (it must NOT be folded into inject_css(), which has to
    # stay early -- before the switch-role overlay renders -- or the
    # overlay's own CSS, defined in the same stylesheet, wouldn't be
    # loaded yet and it would render unstyled).
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)


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
