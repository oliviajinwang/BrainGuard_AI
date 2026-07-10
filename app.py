import time

import streamlit as st

from utils.db import init_db  # stores patient data(patient history)
from utils.layout import inject_css  #colors/design

st.set_page_config(
    page_title="BrainGuard AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()  # creates database.db here if it doesn't exist yet
inject_css()  # applies the CSS design to the page

if not st.session_state.get("_models_preloaded", False):
    # First-ever load in this browser session: import the prediction
    # modules now (Welcome screen) instead of leaving it as a hidden
    # ~5s pause the first time a user opens a prediction page (joblib.load
    # transitively imports xgboost/shap/scikit-learn on first use).
    with st.spinner("Loading prediction models..."):
        import src.predict  # noqa: F401
        import src.predict_lifestyle  # noqa: F401
    st.session_state["_models_preloaded"] = True

st.session_state.setdefault("role", None)
st.session_state.setdefault("clinic_authenticated", False)
st.session_state.setdefault("show_about", False)
st.session_state.setdefault("_switching", None)
st.session_state.setdefault("selected_patient", None)
st.session_state.setdefault("selected_patient_id", None)
st.session_state.setdefault("selected_patient_record", None)
st.session_state.setdefault("history_last_selection", None)
st.session_state.setdefault("reload_patient_record", False)


def _start_switch_role():
    st.session_state._switching = "overlay"


# Two-phase switch: the on_click callback alone (reset role, rerun) already
# stops the dashboard's Python code from re-executing, but the browser can
# still lag in pruning the *previous* render's stale DOM (verified: caught a
# brief dashboard/role-select overlap in ~2 of 6 rapid trials). An opaque
# full-viewport overlay guarantees nothing stale is visible regardless of
# that reconciliation timing, instead of just hoping it resolves fast enough.
if st.session_state._switching == "overlay":
    with st.container(key="switching_overlay"):
        st.write("Logging out...")
    time.sleep(0.15)
    st.session_state._switching = "commit"
    st.rerun()

if st.session_state._switching == "commit":
    st.session_state.role = None
    st.session_state.clinic_authenticated = False
    st.session_state.selected_patient = None
    st.session_state.selected_patient_id = None
    st.session_state.selected_patient_record = None
    st.session_state.history_last_selection = None
    st.session_state.reload_patient_record = True
    st.session_state._switching = None

if st.session_state.role is None:
    if st.session_state.show_about:
        # Independent of the patient/clinic portals: reachable straight
        # from the Welcome screen's "About" link, with its own way back.
        nav = st.navigation([st.Page("views/about.py", title="About")], position="hidden")
        nav.run()
    else:
        nav = st.navigation([st.Page("views/role_select.py", title="Welcome")], position="hidden")
        nav.run()

elif st.session_state.role == "patient":
    st.sidebar.markdown("### Patient Portal")
    st.sidebar.markdown("---")

    pages = [
        st.Page("views/patient_check.py", title="Quick Risk Check", default=True),
        st.Page("views/register_patient.py", title="Register Patient"),
        st.Page("views/dementia_check.py", title="Dementia Check"),
        st.Page("views/medical_report.py", title="Medical Report"),
    ]
    nav = st.navigation(pages)
    st.button("Switch Role", on_click=_start_switch_role, key="switch_role_btn")
    nav.run()

elif st.session_state.role == "clinic":
    if not st.session_state.clinic_authenticated:
        nav = st.navigation([st.Page("views/clinic_login.py", title="Clinic Login")], position="hidden")
        nav.run()
    else:
        st.sidebar.markdown("### Clinic Portal")
        st.sidebar.markdown("---")

        pages = [
            st.Page("views/dashboard.py", title="Dashboard", default=True),
            st.Page("views/history.py", title="Patient History"),
            st.Page(
                "views/patient_detail.py",
                title="Patient Detail",
                url_path="patient-detail",
                visibility="hidden",
            ),
        ]
        nav = st.navigation(pages)
        st.button("Log Out / Switch Role", on_click=_start_switch_role, key="switch_role_btn")
        nav.run()
