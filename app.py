import importlib
import time

import streamlit as st

import utils.db as _db

# Long-lived Streamlit servers can keep a stale utils.db in sys.modules after
# git pulls. Reload when clinician auth helpers are missing so clinic login
# does not crash with ImportError.
if not hasattr(_db, "create_clinician"):
    _db = importlib.reload(_db)

from utils.db import get_clinician_profile, init_db  # stores patient data(patient history)
from utils.i18n import apply_clinician_language, t
from utils.layout import hide_sidebar, inject_css  #colors/design

st.set_page_config(
    page_title="BrainGuard AI",
    layout="wide",
    # "auto" (not "expanded") -- expanded forces the sidebar open even on a
    # phone-width viewport, where it eats most of the screen and leaves the
    # actual page content squeezed into a sliver. "auto" keeps desktop
    # behavior identical (still opens by default above Streamlit's ~768px
    # breakpoint) while letting it collapse on mobile as designed.
    initial_sidebar_state="auto",
)

init_db()  # creates database.db here if it doesn't exist yet
inject_css()  # applies the CSS design to the page -- must run before the
              # switch-role overlay below, or its own styling won't be
              # loaded yet and it will render unstyled.

if not st.session_state.get("_models_preloaded", False):
    with st.spinner("Loading prediction models..."):
        import src.predict  # noqa: F401
        import src.predict_lifestyle  # noqa: F401
    st.session_state["_models_preloaded"] = True

st.session_state.setdefault("role", None)
st.session_state.setdefault("clinic_authenticated", False)
st.session_state.setdefault("clinic_user", None)
st.session_state.setdefault("clinic_display_name", None)
st.session_state.setdefault("clinic_clinician_id", None)
st.session_state.setdefault("ui_language", "en")
st.session_state.setdefault("show_role_select", False)
st.session_state.setdefault("_switching", None)
st.session_state.setdefault("selected_patient", None)
st.session_state.setdefault("selected_patient_id", None)
st.session_state.setdefault("selected_patient_record", None)
st.session_state.setdefault("patient_record", None)
st.session_state.setdefault("patient_record_id", None)
st.session_state.setdefault("history_last_selection", None)
st.session_state.setdefault("reload_patient_record", False)


def _start_switch_role():
    st.session_state._switching = "overlay"


if st.session_state._switching == "overlay":
    hide_sidebar()
    with st.container(key="switching_overlay"):
        st.write(t("logging_out"))
    time.sleep(0.15)
    st.session_state._switching = "commit"
    st.rerun()

if st.session_state._switching == "commit":
    st.session_state.role = None
    st.session_state.clinic_authenticated = False
    st.session_state.clinic_user = None
    st.session_state.clinic_display_name = None
    st.session_state.clinic_clinician_id = None
    st.session_state.dp_edit_mode = False
    st.session_state.ui_language = "en"
    st.session_state.pop("_language_loaded_for", None)
    st.session_state.selected_patient = None
    st.session_state.selected_patient_id = None
    st.session_state.selected_patient_record = None
    st.session_state.patient_record = None
    st.session_state.patient_record_id = None
    st.session_state.assistant_messages = []
    st.session_state.assistant_patient_id = None
    st.session_state.assistant_pending_patient_id = None
    st.session_state.history_last_selection = None
    st.session_state.reload_patient_record = True
    st.session_state._switching = None

# st.session_state.role is now final for this run -- safe to decide whether
# to hide the sidebar (see hide_sidebar()'s docstring for why this can't
# just live inside inject_css() above).
if st.session_state.role is None or (
    st.session_state.role == "clinic" and not st.session_state.clinic_authenticated
):
    hide_sidebar()

if st.session_state.role is None:
    if st.session_state.show_role_select:
        nav = st.navigation([st.Page("views/role_select.py", title="Select Role")], position="hidden")
        nav.run()
    else:
        nav = st.navigation([st.Page("views/welcome.py", title="Welcome")], position="hidden")
        nav.run()

elif st.session_state.role == "patient":
    st.sidebar.markdown("### Patient Portal")
    st.sidebar.markdown("---")

    pages = [
        st.Page("views/patient_check.py", title="Quick Risk Check", default=True),
        st.Page("views/register_patient.py", title="Register Patient"),
        st.Page("views/assistant.py", title="My AI Assistant"),
    ]
    nav = st.navigation(pages)
    st.button("Switch Role", on_click=_start_switch_role, key="switch_role_btn")
    nav.run()

elif st.session_state.role == "clinic":
    if not st.session_state.clinic_authenticated:
        nav = st.navigation([st.Page("views/clinic_login.py", title="Clinic Login")], position="hidden")
        nav.run()
    else:
        # Keep the UI language aligned with the logged-in doctor's preference.
        username = st.session_state.get("clinic_user")
        if username and not st.session_state.get("_language_loaded_for") == username:
            account = get_clinician_profile(username)
            if account:
                apply_clinician_language(account["profile"].get("preferred_language"))
            st.session_state._language_loaded_for = username

        st.sidebar.markdown(f"### {t('clinic_portal')}")
        st.sidebar.caption(
            f"{t('logged_in_as')} **{st.session_state.clinic_display_name or st.session_state.clinic_user}**"
        )
        st.sidebar.markdown("---")

        pages = [
            st.Page("views/dashboard.py", title=t("nav_dashboard"), default=True),
            st.Page("views/history.py", title=t("nav_history")),
            st.Page("views/patient_ai_conversation.py", title=t("nav_ai_conversation")),
            st.Page("views/dementia_check.py", title=t("nav_dementia_check")),
            st.Page("views/medical_report.py", title=t("nav_medical_report")),
            st.Page(
                "views/doctor_profile.py",
                title=t("nav_my_profile"),
                icon=":material/account_circle:",
            ),
            st.Page(
                "views/patient_detail.py",
                title=t("nav_patient_detail"),
                url_path="patient-detail",
                visibility="hidden",
            ),
        ]
        nav = st.navigation(pages)
        st.button(t("switch_role"), on_click=_start_switch_role, key="switch_role_btn")
        nav.run()
