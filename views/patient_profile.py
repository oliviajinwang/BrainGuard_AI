"""Patient-side My Profile page.

Loads and edits the signed-in patient's own record by Patient ID.
Does not modify or duplicate the Dementia Risk Check page.
"""

from __future__ import annotations

import copy
import hashlib
from datetime import date
from html import escape

import streamlit as st

from utils.avatar import make_circular_avatar_data_url
from utils.db import (
    display_id,
    get_assessment_history,
    get_patient,
    load_patient_record,
    patient_has_pin,
    save_patient_record,
    set_patient_pin,
    verify_patient_pin,
)
from utils.i18n import PATIENT_LANGUAGE_OPTIONS, apply_patient_language, normalize_patient_language, t
from utils.patient_conversation import get_patient_conversation, summarize_conversation
from utils.patient_record import default_portal_profile, parse_iso_date
from utils.response_source import latest_response_source_label
from utils import pin_lockout

_PROFILE_CSS = """
<style>
.pp-page {
    animation: pp-fade-up 0.34s cubic-bezier(0.4, 0, 0.2, 1) both;
    max-width: 1120px;
}
.pp-title {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 34px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--ink-primary, #102A43);
    margin: 0 0 0.35rem 0;
}
.pp-subtitle {
    font-size: 14px;
    color: var(--ink-muted, #627482);
    margin: 0 0 1.5rem 0;
    line-height: 1.5;
}
.pp-section-title {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 20px;
    font-weight: 600;
    color: var(--ink-primary, #102A43);
    margin: 0 0 0.3rem 0;
}
.pp-section-caption {
    font-size: 13px;
    color: var(--ink-muted, #627482);
    margin: 0 0 1rem 0;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(20, 40, 65, 0.10) !important;
    border-radius: 18px !important;
    box-shadow: 0 2px 10px rgba(20, 40, 65, 0.05) !important;
    animation: pp-fade-up 0.34s cubic-bezier(0.4, 0, 0.2, 1) both;
}
.pp-avatar-wrap {
    position: relative;
    width: 128px;
    height: 128px;
}
.pp-avatar, .pp-avatar-img {
    width: 128px;
    height: 128px;
    border-radius: 50%;
    transition: transform 0.28s ease;
}
.pp-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--brand-navy, #102A43);
    color: white;
    font-size: 2.1rem;
    font-weight: 700;
    box-shadow: 0 8px 20px rgba(16, 42, 67, 0.18);
}
.pp-avatar-img {
    object-fit: cover;
    border: 3px solid rgba(39, 109, 104, 0.25);
    box-shadow: 0 8px 20px rgba(16, 42, 67, 0.12);
}
.pp-avatar-wrap:hover .pp-avatar,
.pp-avatar-wrap:hover .pp-avatar-img { transform: scale(1.02); }
.st-key-pp_avatar_block {
    position: relative !important;
    width: 128px !important;
    min-height: 128px !important;
}
.st-key-pp_camera_upload {
    position: absolute !important;
    right: -2px !important;
    bottom: 2px !important;
    width: 40px !important;
    z-index: 8 !important;
}
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzone"] {
    min-height: 36px !important;
    height: 36px !important;
    width: 36px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    border: 2.5px solid #FFFFFF !important;
    background: var(--brand, #276D68) !important;
    box-shadow: 0 4px 12px rgba(16, 42, 67, 0.30) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    transition: transform 0.2s ease, filter 0.2s ease !important;
}
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzone"]:hover {
    transform: scale(1.1) !important;
    filter: brightness(1.12);
}
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzone"] > *,
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzoneInstructions"],
.st-key-pp_camera_upload label,
.st-key-pp_camera_upload [data-testid="stFileUploaderFile"] {
    display: none !important;
}
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzone"] input[type="file"] {
    display: block !important;
    opacity: 0 !important;
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    cursor: pointer !important;
    z-index: 2 !important;
}
.st-key-pp_camera_upload [data-testid="stFileUploaderDropzone"]::after {
    content: "";
    width: 16px;
    height: 16px;
    display: block;
    background-color: #FFFFFF;
    pointer-events: none;
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M9 3.5a1 1 0 0 1 .8-.4h4.4a1 1 0 0 1 .8.4l.9 1.1H19a2.5 2.5 0 0 1 2.5 2.5v10A2.5 2.5 0 0 1 19 19.6H5A2.5 2.5 0 0 1 2.5 17.1v-10A2.5 2.5 0 0 1 5 4.6h2.1L9 3.5Zm3 13.1a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Zm0-1.8a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8Z'/%3E%3C/svg%3E") center / contain no-repeat;
    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M9 3.5a1 1 0 0 1 .8-.4h4.4a1 1 0 0 1 .8.4l.9 1.1H19a2.5 2.5 0 0 1 2.5 2.5v10A2.5 2.5 0 0 1 19 19.6H5A2.5 2.5 0 0 1 2.5 17.1v-10A2.5 2.5 0 0 1 5 4.6h2.1L9 3.5Zm3 13.1a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Zm0-1.8a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8Z'/%3E%3C/svg%3E") center / contain no-repeat;
}
.pp-name {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 28px;
    font-weight: 700;
    color: var(--ink-primary, #102A43);
    margin: 0 0 0.35rem 0;
}
.pp-meta {
    font-size: 14px;
    color: var(--ink-secondary, #3E5668);
    margin: 0 0 0.25rem 0;
}
.pp-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.55rem 1.25rem;
    margin-top: 0.9rem;
    padding-top: 0.85rem;
    border-top: 1px solid rgba(20, 40, 65, 0.08);
}
.pp-label {
    display: block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-muted, #627482);
    margin-bottom: 0.12rem;
}
.pp-value {
    font-size: 14px;
    color: var(--ink-secondary, #3E5668);
    line-height: 1.4;
}
.pp-row {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 0.8rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid rgba(20, 40, 65, 0.07);
}
.pp-row:last-child { border-bottom: none; }
.pp-row .left {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--ink-muted, #627482);
}
.pp-row .right {
    font-size: 15px;
    color: var(--ink-primary, #102A43);
}
.pp-health-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75rem;
}
.pp-badge {
    background: #F8FAFC;
    border: 1px solid rgba(20, 40, 65, 0.08);
    border-radius: 14px;
    padding: 0.9rem 1rem;
}
.pp-badge .k {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink-muted, #627482);
}
.pp-badge .v {
    margin-top: 0.35rem;
    font-size: 15px;
    font-weight: 700;
    color: var(--ink-primary, #102A43);
}
.pp-badge .v.yes { color: var(--moderate, #8A5A00); }
.pp-badge .v.no { color: var(--good, #256C4C); }
.pp-spacer { height: 1.15rem; }
.pp-toast {
    position: fixed;
    top: 22px;
    right: 24px;
    z-index: 100000;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.85rem 1.15rem;
    border-radius: 14px;
    background: #FFFFFF;
    border: 1px solid rgba(37, 108, 76, 0.25);
    box-shadow: 0 8px 24px rgba(16, 42, 67, 0.14);
    font-weight: 700;
    font-size: 14px;
    animation: pp-toast-in 0.3s ease both, pp-toast-out 0.35s ease 2.4s forwards;
}
.pp-toast-check {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--good, #256C4C);
    color: white;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.st-key-pp_edit_panel {
    animation: pp-fade-up 0.42s cubic-bezier(0.22, 1, 0.36, 1) both !important;
}
@keyframes pp-fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pp-toast-in {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pp-toast-out {
    from { opacity: 1; }
    to { opacity: 0; visibility: hidden; }
}
@media (max-width: 900px) {
    .pp-health-grid { grid-template-columns: 1fr 1fr; }
    .pp-details { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
    .pp-health-grid { grid-template-columns: 1fr; }
}
</style>
"""


def _initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _resolve_patient_id(text: str) -> int | None:
    q = text.strip().upper().removeprefix("P")
    if not q.isdigit():
        return None
    patient_id = int(q)
    return patient_id if get_patient(patient_id) else None


def _section(title: str, caption: str = "") -> None:
    caption_html = f'<p class="pp-section-caption">{escape(caption)}</p>' if caption else ""
    st.markdown(
        f'<h2 class="pp-section-title">{escape(title)}</h2>{caption_html}',
        unsafe_allow_html=True,
    )


def _yes_no(flag: bool) -> tuple[str, str]:
    return (t("yes"), "yes") if flag else (t("no"), "no")


def _gender_label(value: str) -> str:
    return {"Female": t("female"), "Male": t("male"), "Other": t("other")}.get(value, value)


def _nearest_appointment(appointments: list[dict]) -> dict | None:
    today = date.today().isoformat()
    upcoming = []
    for item in appointments or []:
        day = str(item.get("date") or "")
        if day >= today:
            upcoming.append(item)
    if not upcoming:
        return None
    upcoming.sort(key=lambda item: (item.get("date") or "", item.get("time") or ""))
    return upcoming[0]


def _latest_assessment(patient_id: int, record: dict) -> dict:
    overview = record.get("overview") or {}
    history = get_assessment_history(patient_id)
    if not history.empty:
        latest = history.iloc[-1]
        return {
            "date": str(latest.get("recorded_at") or "")[:19].replace("T", " "),
            "label": latest.get("prediction_label") or overview.get("prediction_label") or "Pending",
            "probability": latest.get("risk_percent")
            if latest.get("risk_percent") is not None
            else overview.get("confidence"),
            "type": latest.get("assessment_type") or overview.get("assessment_type") or "—",
            "recommendation": "",
        }
    notes = record.get("doctor_notes") or []
    recommendation = ""
    if notes:
        recommendation = str(notes[-1].get("text") or notes[-1].get("note") or "")
    return {
        "date": overview.get("registration_date") or "—",
        "label": overview.get("prediction_label") or "Pending",
        "probability": overview.get("confidence"),
        "type": overview.get("assessment_type") or "—",
        "recommendation": recommendation,
    }


def _sign_out() -> None:
    st.session_state.patient_portal_id = None
    st.session_state.patient_portal_pending_id = None
    st.session_state.pp_edit_mode = False


st.markdown(_PROFILE_CSS, unsafe_allow_html=True)
st.markdown("<div class='pp-page'>", unsafe_allow_html=True)
st.warning(t("profile_warning"))

st.session_state.setdefault("patient_portal_id", None)
st.session_state.setdefault("patient_portal_pending_id", None)
st.session_state.setdefault("pp_edit_mode", False)
st.session_state.setdefault("pp_form_nonce", 0)
st.session_state.setdefault("pp_last_photo_digest", None)

# Reuse an already-authenticated AI Assistant session for the same patient.
if not st.session_state.patient_portal_id and st.session_state.get("assistant_patient_id"):
    st.session_state.patient_portal_id = int(st.session_state.assistant_patient_id)

patient_id = st.session_state.get("patient_portal_id")
pending_id = st.session_state.get("patient_portal_pending_id")

# ---- Sign-in gate (Patient ID + PIN) ----
if not patient_id and not pending_id:
    st.markdown(f"<h1 class='pp-title'>{escape(t('my_profile'))}</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p class='pp-subtitle'>{escape(t('profile_subtitle'))}</p>",
        unsafe_allow_html=True,
    )
    st.info(t("sign_in_prompt"))
    st.caption(
        "A trusted family member or caregiver may help you sign in. Adding someone as a "
        "trusted contact below does not by itself give them access to your account."
    )
    identity = st.text_input(t("patient_id"), placeholder="e.g. P0006", key="pp_sign_in_query")
    if st.button(t("continue"), type="primary", key="pp_continue"):
        resolved = _resolve_patient_id(identity) if identity.strip() else None
        if resolved is None:
            st.error(t("no_patient_match"))
        else:
            st.session_state.patient_portal_pending_id = resolved
            st.rerun()
    st.stop()

if pending_id and not patient_id:
    st.markdown(f"<h1 class='pp-title'>{escape(t('my_profile'))}</h1>", unsafe_allow_html=True)
    pending_row = get_patient(pending_id)
    if pending_row is None:
        st.session_state.patient_portal_pending_id = None
        st.error(t("record_missing"))
        st.stop()

    if st.button(t("use_different_id"), key="pp_back_id"):
        st.session_state.patient_portal_pending_id = None
        st.rerun()

    label = display_id(pending_id)
    name = pending_row["full_name"]
    if patient_has_pin(pending_id):
        st.markdown(f"#### {t('enter_pin_for', name=name, label=label)}")
        if pin_lockout.seconds_remaining(pending_id) > 0:
            st.error(t("pin_locked"))
        else:
            pin_entry = st.text_input(t("pin_label"), type="password", max_chars=6, key="pp_pin_entry")
            if st.button(t("unlock"), type="primary", key="pp_unlock"):
                if verify_patient_pin(pending_id, pin_entry):
                    pin_lockout.record_success(pending_id)
                    st.session_state.patient_portal_id = int(pending_id)
                    st.session_state.patient_portal_pending_id = None
                    st.session_state.assistant_patient_id = int(pending_id)
                    st.session_state.pop("_patient_language_loaded_for", None)
                    st.rerun()
                else:
                    pin_lockout.record_failure(pending_id)
                    if pin_lockout.seconds_remaining(pending_id) > 0:
                        st.error(t("pin_locked"))
                    else:
                        st.error(t("incorrect_pin"))
    else:
        st.markdown(f"#### {t('setup_pin_for', name=name, label=label)}")
        new_pin = st.text_input(t("set_pin_label"), type="password", max_chars=6, key="pp_new_pin")
        new_pin_confirm = st.text_input(t("confirm_pin"), type="password", max_chars=6, key="pp_new_pin_confirm")
        if st.button(t("set_pin_continue"), type="primary", key="pp_set_pin"):
            if not new_pin.isdigit() or not (4 <= len(new_pin) <= 6):
                st.error(t("pin_digits_error"))
            elif new_pin != new_pin_confirm:
                st.error(t("pins_mismatch"))
            else:
                set_patient_pin(pending_id, new_pin)
                st.session_state.patient_portal_id = int(pending_id)
                st.session_state.patient_portal_pending_id = None
                st.session_state.assistant_patient_id = int(pending_id)
                st.session_state.pop("_patient_language_loaded_for", None)
                st.rerun()
    st.stop()

# ---- Load this patient's record only ----
try:
    record = load_patient_record(int(patient_id))
except ValueError:
    st.error(t("record_gone"))
    _sign_out()
    st.stop()

portal = record.setdefault("portal_profile", default_portal_profile())
for key, value in default_portal_profile().items():
    portal.setdefault(key, value)
portal["preferred_language"] = normalize_patient_language(portal.get("preferred_language"))
apply_patient_language(portal["preferred_language"])
st.session_state._patient_language_loaded_for = int(patient_id)

st.markdown(f"<h1 class='pp-title'>{escape(t('my_profile'))}</h1>", unsafe_allow_html=True)
st.markdown(
    f"<p class='pp-subtitle'>{escape(t('profile_subtitle'))}</p>",
    unsafe_allow_html=True,
)

overview = record["overview"]
risk = record["risk_profile"]
contact = record["contact"]
edit_mode = bool(st.session_state.pp_edit_mode)
form_nonce = int(st.session_state.pp_form_nonce)
patient_name = overview.get("name") or t("patient_id")
patient_label = overview.get("patient_id") or display_id(patient_id)

top_right, _ = st.columns([1, 3])
with top_right:
    if st.button(t("switch_patient"), key="pp_switch_patient"):
        _sign_out()
        st.rerun()

# 1) Profile Header -------------------------------------------------------
with st.container(border=True, key="pp_header_card"):
    left, right = st.columns([0.9, 2.4], gap="large")
    with left:
        with st.container(key="pp_avatar_block"):
            photo = str(portal.get("photo_data_url") or "")
            if photo.startswith("data:image"):
                st.markdown(
                    f'<div class="pp-avatar-wrap"><img class="pp-avatar-img" src="{escape(photo, quote=True)}" alt="Patient photo" /></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="pp-avatar-wrap"><div class="pp-avatar">{escape(_initials(patient_name))}</div></div>',
                    unsafe_allow_html=True,
                )
            upload = st.file_uploader(
                "Change photo",
                type=["png", "jpg", "jpeg", "webp"],
                key="pp_camera_upload",
                label_visibility="collapsed",
            )
        if upload is not None:
            digest = hashlib.sha1(upload.getvalue()).hexdigest()
            if st.session_state.get("pp_last_photo_digest") != digest:
                try:
                    portal["photo_data_url"] = make_circular_avatar_data_url(upload.getvalue())
                    record["portal_profile"] = portal
                    save_patient_record(int(patient_id), record, modified_by=patient_label)
                    st.session_state.pp_last_photo_digest = digest
                    st.session_state.pp_save_success = True
                    st.rerun()
                except Exception:
                    st.error(t("photo_save_error"))

    with right:
        st.markdown(f'<p class="pp-name">{escape(patient_name)}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<p class="pp-meta">{escape(t("patient_id"))} <strong>{escape(patient_label)}</strong></p>',
            unsafe_allow_html=True,
        )
        gender_display = _gender_label(overview.get("gender") or "") if overview.get("gender") else "—"
        st.markdown(
            f"""
            <div class="pp-details">
              <div><span class="pp-label">{escape(t("age"))}</span><span class="pp-value">{int(overview.get('age') or 0)}</span></div>
              <div><span class="pp-label">{escape(t("gender"))}</span><span class="pp-value">{escape(gender_display)}</span></div>
              <div><span class="pp-label">{escape(t("registered"))}</span><span class="pp-value">{escape(overview.get('registration_date') or '—')}</span></div>
              <div><span class="pp-label">{escape(t("primary_doctor"))}</span><span class="pp-value">{escape(portal.get('primary_doctor') or t("not_set"))}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not edit_mode:
            st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
            btn_col, _ = st.columns([1, 2])
            with btn_col:
                if st.button(t("edit_profile"), type="primary", key="pp_edit_btn", use_container_width=True):
                    st.session_state.pp_edit_mode = True
                    st.session_state.pp_edit_snapshot = copy.deepcopy(record)
                    st.session_state.pp_form_nonce = form_nonce + 1
                    st.rerun()

# 2) Personal Information / Edit panel ------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
if edit_mode:
    with st.container(border=True, key="pp_edit_panel"):
        _section(t("personal_information"), t("personal_info_edit_caption"))
        c1, c2 = st.columns(2, gap="large")
        with c1:
            overview["name"] = st.text_input(t("full_name"), overview.get("name", ""), key=f"pp_name_{form_nonce}")
            dob_value = parse_iso_date(portal.get("date_of_birth") or "") if portal.get("date_of_birth") else None
            dob = st.date_input(
                t("date_of_birth"),
                value=dob_value or date(1960, 1, 1),
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                key=f"pp_dob_{form_nonce}",
            )
            portal["date_of_birth"] = dob.isoformat()
            overview["age"] = int(
                st.number_input(
                    t("age"),
                    min_value=0,
                    max_value=120,
                    value=int(overview.get("age") or 0),
                    key=f"pp_age_{form_nonce}",
                )
            )
            overview["gender"] = st.selectbox(
                t("gender"),
                ["Female", "Male", "Other"],
                index=["Female", "Male", "Other"].index(overview.get("gender"))
                if overview.get("gender") in ["Female", "Male", "Other"]
                else 0,
                format_func=_gender_label,
                key=f"pp_gender_{form_nonce}",
            )
            contact["email"] = st.text_input(t("email"), contact.get("email", ""), key=f"pp_email_{form_nonce}")
        with c2:
            contact["phone"] = st.text_input(t("phone"), contact.get("phone", ""), key=f"pp_phone_{form_nonce}")
            contact["address"] = st.text_area(t("address"), contact.get("address", ""), key=f"pp_address_{form_nonce}")
            risk["education_years"] = int(
                st.number_input(
                    t("education_years"),
                    min_value=0,
                    max_value=30,
                    value=int(risk.get("education_years") or 0),
                    key=f"pp_edu_{form_nonce}",
                )
            )
            current_lang = normalize_patient_language(portal.get("preferred_language"))
            portal["preferred_language"] = st.selectbox(
                t("preferred_language"),
                PATIENT_LANGUAGE_OPTIONS,
                index=PATIENT_LANGUAGE_OPTIONS.index(current_lang),
                key=f"pp_lang_{form_nonce}",
            )
            portal["primary_doctor"] = st.text_input(
                t("primary_doctor"),
                portal.get("primary_doctor", ""),
                key=f"pp_doctor_{form_nonce}",
            )

        st.markdown(f"##### {t('emergency_contact')}")
        e1, e2 = st.columns(2, gap="large")
        with e1:
            portal["emergency_name"] = st.text_input(
                t("contact_name"), portal.get("emergency_name", ""), key=f"pp_em_name_{form_nonce}"
            )
            portal["emergency_relationship"] = st.text_input(
                t("relationship"), portal.get("emergency_relationship", ""), key=f"pp_em_rel_{form_nonce}"
            )
        with e2:
            portal["emergency_phone"] = st.text_input(
                t("phone_number"), portal.get("emergency_phone", ""), key=f"pp_em_phone_{form_nonce}"
            )
            portal["emergency_email"] = st.text_input(
                t("email"), portal.get("emergency_email", ""), key=f"pp_em_email_{form_nonce}"
            )

        st.markdown(f"##### {t('trusted_contact')}")
        st.caption(t("trusted_contact_caption"))
        tc1, tc2 = st.columns(2, gap="large")
        with tc1:
            portal["trusted_contact_name"] = st.text_input(
                t("contact_name"), portal.get("trusted_contact_name", ""), key=f"pp_tc_name_{form_nonce}"
            )
            portal["trusted_contact_relationship"] = st.text_input(
                t("relationship"), portal.get("trusted_contact_relationship", ""), key=f"pp_tc_rel_{form_nonce}"
            )
        with tc2:
            portal["trusted_contact_email_or_phone"] = st.text_input(
                t("trusted_contact_email_or_phone"),
                portal.get("trusted_contact_email_or_phone", ""),
                key=f"pp_tc_contact_{form_nonce}",
            )

        st.markdown(f"##### {t('health_overview_edit')}")
        h1, h2 = st.columns(2)
        with h1:
            risk["diabetes"] = st.toggle(t("diabetes"), value=bool(risk.get("diabetes")), key=f"pp_diabetes_{form_nonce}")
            risk["hypertension"] = st.toggle(
                t("hypertension"), value=bool(risk.get("hypertension")), key=f"pp_hyper_{form_nonce}"
            )
            risk["high_cholesterol"] = st.toggle(
                t("high_cholesterol"), value=bool(risk.get("high_cholesterol")), key=f"pp_chol_{form_nonce}"
            )
            risk["smoking"] = st.toggle(t("smoking"), value=bool(risk.get("smoking")), key=f"pp_smoke_{form_nonce}")
        with h2:
            record["allergies"] = st.text_area(
                t("known_allergies"),
                record.get("allergies") or "",
                key=f"pp_allergies_{form_nonce}",
                height=80,
            )
            meds_text = st.text_area(
                t("current_medications_hint"),
                "\n".join(
                    m.get("name", "") if isinstance(m, dict) else str(m)
                    for m in (record.get("medications") or [])
                ),
                key=f"pp_meds_{form_nonce}",
                height=80,
            )
            record["medications"] = [
                {"name": line.strip(), "dosage": "", "frequency": ""}
                for line in meds_text.splitlines()
                if line.strip()
            ]

        st.text_input(t("patient_id"), patient_label, disabled=True, key=f"pp_id_ro_{form_nonce}")

        record["overview"] = overview
        record["risk_profile"] = risk
        record["contact"] = contact
        record["portal_profile"] = portal

        save_col, cancel_col, _ = st.columns([1, 1, 2])
        with save_col:
            if st.button(t("save_changes"), type="primary", key="pp_save_btn", use_container_width=True):
                with st.spinner(t("saving_profile")):
                    portal["preferred_language"] = normalize_patient_language(portal.get("preferred_language"))
                    record["portal_profile"] = portal
                    save_patient_record(int(patient_id), record, modified_by=patient_label)
                apply_patient_language(portal["preferred_language"])
                st.session_state._patient_language_loaded_for = int(patient_id)
                st.session_state.pp_edit_mode = False
                st.session_state.pop("pp_edit_snapshot", None)
                st.session_state.pp_save_success = True
                st.rerun()
        with cancel_col:
            if st.button(t("cancel"), key="pp_cancel_btn", use_container_width=True):
                st.session_state.pp_edit_mode = False
                st.session_state.pop("pp_edit_snapshot", None)
                st.session_state.pp_form_nonce = form_nonce + 1
                st.rerun()
else:
    with st.container(border=True):
        _section(t("personal_information"), t("personal_info_view_caption"))
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('full_name'))}</div><div class='right'>{escape(overview.get('name') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('date_of_birth'))}</div><div class='right'>{escape(portal.get('date_of_birth') or t('not_set'))}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('email'))}</div><div class='right'>{escape(contact.get('email') or t('not_set'))}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('phone'))}</div><div class='right'>{escape(contact.get('phone') or t('not_set'))}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('address'))}</div><div class='right'>{escape(contact.get('address') or t('not_set'))}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('education_years'))}</div><div class='right'>{int(risk.get('education_years') or 0)}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('preferred_language'))}</div><div class='right'>{escape(portal.get('preferred_language') or 'English')}</div></div>",
            unsafe_allow_html=True,
        )

# 3) Health Overview ------------------------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
with st.container(border=True):
    _section(t("health_overview"), t("health_overview_caption"))
    diabetes_text, diabetes_cls = _yes_no(bool(risk.get("diabetes")))
    hyper_text, hyper_cls = _yes_no(bool(risk.get("hypertension")))
    chol_text, chol_cls = _yes_no(bool(risk.get("high_cholesterol")))
    smoke_text, smoke_cls = _yes_no(bool(risk.get("smoking")))
    allergies = (record.get("allergies") or "").strip() or t("none_reported")
    meds = record.get("medications") or []
    if meds:
        med_names = [
            (m.get("name") if isinstance(m, dict) else str(m)).strip()
            for m in meds
        ]
        meds_display = ", ".join(name for name in med_names if name) or t("none_listed")
    else:
        meds_display = t("none_listed")
    st.markdown(
        f"""
        <div class="pp-health-grid">
          <div class="pp-badge"><div class="k">{escape(t("diabetes"))}</div><div class="v {diabetes_cls}">{diabetes_text}</div></div>
          <div class="pp-badge"><div class="k">{escape(t("hypertension"))}</div><div class="v {hyper_cls}">{hyper_text}</div></div>
          <div class="pp-badge"><div class="k">{escape(t("high_cholesterol"))}</div><div class="v {chol_cls}">{chol_text}</div></div>
          <div class="pp-badge"><div class="k">{escape(t("smoking_status"))}</div><div class="v {smoke_cls}">{smoke_text}</div></div>
          <div class="pp-badge"><div class="k">{escape(t("known_allergies"))}</div><div class="v">{escape(allergies)}</div></div>
          <div class="pp-badge"><div class="k">{escape(t("current_medications"))}</div><div class="v">{escape(meds_display)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 4) Latest Dementia Assessment -------------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
assessment = _latest_assessment(int(patient_id), record)
with st.container(border=True):
    _section(t("latest_dementia_assessment"), t("assessment_caption"))
    prob = assessment.get("probability")
    prob_text = f"{float(prob):.1f}%" if prob not in (None, "") else "—"
    st.markdown(
        f"<div class='pp-row'><div class='left'>{escape(t('assessment_date'))}</div><div class='right'>{escape(str(assessment.get('date') or '—'))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('risk_label'))}</div><div class='right'>{escape(str(assessment.get('label') or 'Pending'))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('estimated_probability'))}</div><div class='right'>{escape(prob_text)}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('assessment_type'))}</div><div class='right'>{escape(str(assessment.get('type') or '—'))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('response_source'))}</div><div class='right'>{escape(latest_response_source_label(int(patient_id)))}</div></div>",
        unsafe_allow_html=True,
    )
    recommendation = str(assessment.get("recommendation") or "").strip()
    if recommendation:
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('doctor_recommendation'))}</div><div class='right'>{escape(recommendation)}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(t("no_doctor_recommendation"))
    if st.button(t("view_full_risk_check"), type="primary", key="pp_open_risk_check"):
        st.switch_page("views/patient_check.py")

# 5) Upcoming Appointment -------------------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
appointment = _nearest_appointment(record.get("appointments") or [])
with st.container(border=True):
    _section(t("upcoming_appointment"), t("appointment_caption"))
    if not appointment:
        st.info(t("no_upcoming_appointments"))
    else:
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('date'))}</div><div class='right'>{escape(appointment.get('date') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('time'))}</div><div class='right'>{escape(appointment.get('time') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('doctor'))}</div><div class='right'>{escape(appointment.get('provider') or appointment.get('doctor') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('department'))}</div><div class='right'>{escape(appointment.get('department') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('visit_type'))}</div><div class='right'>{escape(appointment.get('title') or appointment.get('visit_type') or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('status'))}</div><div class='right'>{escape(appointment.get('status') or t('scheduled'))}</div></div>",
            unsafe_allow_html=True,
        )

# 6) Emergency Contact ----------------------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
with st.container(border=True):
    _section(t("emergency_contact"), t("emergency_caption"))
    em_name = portal.get("emergency_name") or ""
    em_rel = portal.get("emergency_relationship") or ""
    em_phone = portal.get("emergency_phone") or ""
    em_email = portal.get("emergency_email") or ""
    legacy = (contact.get("emergency_contact") or "").strip()
    if not any([em_name, em_rel, em_phone, em_email]) and legacy:
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('contact'))}</div><div class='right'>{escape(legacy)}</div></div>",
            unsafe_allow_html=True,
        )
    elif not any([em_name, em_rel, em_phone, em_email, legacy]):
        st.info(t("no_emergency_contact"))
    else:
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('contact_name'))}</div><div class='right'>{escape(em_name or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('relationship'))}</div><div class='right'>{escape(em_rel or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('phone_number'))}</div><div class='right'>{escape(em_phone or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('email'))}</div><div class='right'>{escape(em_email or '—')}</div></div>",
            unsafe_allow_html=True,
        )

# 6b) Trusted Contact (optional, account/access support -- not medical -----
# emergencies, and not a grant of access on its own; see caption below) ----
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
with st.container(border=True):
    _section(t("trusted_contact"), t("trusted_contact_caption"))
    tc_name = portal.get("trusted_contact_name") or ""
    tc_rel = portal.get("trusted_contact_relationship") or ""
    tc_contact = portal.get("trusted_contact_email_or_phone") or ""
    if not any([tc_name, tc_rel, tc_contact]):
        st.info(t("no_trusted_contact"))
    else:
        st.markdown(
            f"<div class='pp-row'><div class='left'>{escape(t('contact_name'))}</div><div class='right'>{escape(tc_name or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('relationship'))}</div><div class='right'>{escape(tc_rel or '—')}</div></div>"
            f"<div class='pp-row'><div class='left'>{escape(t('trusted_contact_email_or_phone'))}</div><div class='right'>{escape(tc_contact or '—')}</div></div>",
            unsafe_allow_html=True,
        )

# 7) AI Activity Summary --------------------------------------------------
st.markdown("<div class='pp-spacer'></div>", unsafe_allow_html=True)
messages = get_patient_conversation(int(patient_id))
summary = summarize_conversation(messages)
with st.container(border=True):
    _section(t("ai_activity_summary"), t("ai_activity_caption"))
    total = int(summary.get("message_count") or len(messages))
    latest = messages[-1]["timestamp"][:19] if messages else "—"
    topics = summary.get("topic_counts") or {}
    top_topics = ", ".join(name for name, _ in sorted(topics.items(), key=lambda item: item[1], reverse=True)[:3]) or t("none_yet")
    st.markdown(
        f"<div class='pp-row'><div class='left'>{escape(t('total_conversations'))}</div><div class='right'>{escape(t('messages_count', count=total))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('latest_conversation'))}</div><div class='right'>{escape(str(latest))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('frequent_topics'))}</div><div class='right'>{escape(top_topics)}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('memory_concerns'))}</div><div class='right'>{escape(t('mentions_count', count=int(topics.get('Memory') or 0)))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('sleep_concerns'))}</div><div class='right'>{escape(t('mentions_count', count=int(topics.get('Sleep') or 0)))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('mood_concerns'))}</div><div class='right'>{escape(t('mentions_count', count=int(topics.get('Mood / emotion') or 0)))}</div></div>"
        f"<div class='pp-row'><div class='left'>{escape(t('medication_questions'))}</div><div class='right'>{escape(t('mentions_count', count=int(topics.get('Medication') or 0)))}</div></div>",
        unsafe_allow_html=True,
    )
    if st.button(t("open_ai_history"), type="secondary", key="pp_open_ai"):
        st.session_state.assistant_patient_id = int(patient_id)
        st.switch_page("views/assistant.py")

if st.session_state.pop("pp_save_success", False):
    st.success(t("profile_updated"))
    st.info(t("language_updated"))

st.markdown("</div>", unsafe_allow_html=True)
