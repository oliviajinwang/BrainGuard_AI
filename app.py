import importlib
import time

import streamlit as st

import utils.db as _db
import utils.i18n as _i18n

# Long-lived Streamlit servers can keep a stale utils.db in sys.modules after
# git pulls. Reload when clinician auth helpers are missing so clinic login
# does not crash with ImportError.
if not hasattr(_db, "create_clinician"):
    _db = importlib.reload(_db)

# Same for i18n when patient-language helpers were added after the server started.
if not hasattr(_i18n, "PATIENT_LANGUAGE_OPTIONS"):
    _i18n = importlib.reload(_i18n)

# Same for the UI redesign's module updates. Chart modules are checked by
# value because only their theme colors changed; result_view gained new
# functions, so a stale copy crashes views/patient_check.py with
# "cannot import name 'render_lifestyle_result_summary'". Chart modules
# reload first so result_view's re-executed imports bind the fresh objects.
import utils.cohort_chart as _cohort_chart
import utils.gauge as _gauge
import utils.shap_chart as _shap_chart
import utils.result_view as _result_view

if getattr(_gauge, "_BAR", None) != "#102A43":
    _gauge = importlib.reload(_gauge)
if getattr(_shap_chart, "COLOR_INCREASE", None) != "#A63838":
    _shap_chart = importlib.reload(_shap_chart)
if getattr(_cohort_chart, "COLOR_HIGH_RISK", None) != "#A63838":
    _cohort_chart = importlib.reload(_cohort_chart)
if not hasattr(_result_view, "render_lifestyle_result_summary"):
    _result_view = importlib.reload(_result_view)

from utils.db import get_clinician_profile, init_db, load_patient_record  # stores patient data(patient history)
from utils.i18n import (
    PATIENT_LANGUAGE_OPTIONS,
    apply_clinician_language,
    apply_patient_language,
    t,
)
from utils.layout import hide_sidebar, inject_css  #colors/design
from utils.ui import render_portal_header, render_skeleton

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
    # Shimmer placeholder instead of a blank screen for this one-time,
    # first-load cost (model files are read from disk, not re-downloaded).
    loading_slot = st.empty()
    with loading_slot.container():
        st.caption("Loading prediction models…")
        render_skeleton(lines=3, key="models")
    # Each model loads independently so a broken pickle for one model (e.g.
    # a version-incompatible models/clinician_model.pkl) degrades only the
    # pages that need it, instead of crashing every page in the app,
    # including ones -- like the public landing page -- that never touch it.
    try:
        import src.predict  # noqa: F401
    except Exception:
        st.session_state["_clinical_model_error"] = True
    try:
        import src.predict_lifestyle  # noqa: F401
    except Exception:
        st.session_state["_lifestyle_model_error"] = True
    loading_slot.empty()
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
    st.session_state.pop("preferred_language", None)
    st.session_state.pop("_language_loaded_for", None)
    st.session_state.pop("_patient_language_loaded_for", None)
    st.session_state.selected_patient = None
    st.session_state.selected_patient_id = None
    st.session_state.selected_patient_record = None
    st.session_state.patient_record = None
    st.session_state.patient_record_id = None
    st.session_state.assistant_messages = []
    st.session_state.assistant_patient_id = None
    st.session_state.assistant_pending_patient_id = None
    st.session_state.patient_portal_id = None
    st.session_state.patient_portal_pending_id = None
    st.session_state.pp_edit_mode = False
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
    # Keep portal chrome in the signed-in patient's saved preferred language.
    signed_in_patient_id = st.session_state.get("patient_portal_id") or st.session_state.get(
        "assistant_patient_id"
    )
    if signed_in_patient_id and st.session_state.get("_patient_language_loaded_for") != signed_in_patient_id:
        try:
            portal_lang = (
                load_patient_record(int(signed_in_patient_id))
                .get("portal_profile", {})
                .get("preferred_language")
            )
            apply_patient_language(portal_lang)
        except Exception:
            apply_patient_language("English")
        st.session_state._patient_language_loaded_for = signed_in_patient_id
    elif st.session_state.get("preferred_language") not in PATIENT_LANGUAGE_OPTIONS:
        apply_patient_language("English")

    st.sidebar.markdown(f"### {t('patient_portal')}")
    st.sidebar.markdown("---")

    pages = [
        st.Page("views/patient_check.py", title=t("nav_quick_risk_check"), default=True),
        st.Page("views/register_patient.py", title=t("nav_register_patient")),
        st.Page("views/assistant.py", title=t("nav_my_ai_assistant")),
        st.Page(
            "views/patient_profile.py",
            title=t("nav_my_profile"),
            icon=":material/account_circle:",
        ),
    ]
    nav = st.navigation(pages)
    render_portal_header(
        getattr(nav, "title", t("patient_portal")),
        "views/patient_check.py",
        _start_switch_role,
    )
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
        render_portal_header(
            getattr(nav, "title", t("clinic_portal")),
            "views/dashboard.py",
            _start_switch_role,
        )
        nav.run()
