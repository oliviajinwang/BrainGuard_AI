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


def _switch_role():
    st.session_state.role = None
    st.session_state.clinic_authenticated = False


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
    st.sidebar.button("Switch Role", on_click=_switch_role)
    st.sidebar.markdown("---")

    pages = [
        st.Page("views/patient_check.py", title="Quick Risk Check", default=True),
        st.Page("views/register_patient.py", title="Register Patient"),
        st.Page("views/dementia_check.py", title="Dementia Check"),
        st.Page("views/medical_report.py", title="Medical Report"),
        st.Page("views/about.py", title="About"),
    ]
    nav = st.navigation(pages)
    nav.run()

elif st.session_state.role == "clinic":
    if not st.session_state.clinic_authenticated:
        nav = st.navigation([st.Page("views/clinic_login.py", title="Clinic Login")], position="hidden")
        nav.run()
    else:
        st.sidebar.markdown("### Clinic Portal")
        st.sidebar.markdown("---")
        st.sidebar.button("Log Out / Switch Role", on_click=_switch_role)
        st.sidebar.markdown("---")

        pages = [
            st.Page("views/dashboard.py", title="Dashboard", default=True),
            st.Page("views/history.py", title="Patient History"),
            st.Page("views/about.py", title="About"),
        ]
        nav = st.navigation(pages)
        nav.run()
