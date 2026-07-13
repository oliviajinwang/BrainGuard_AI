"""Personalized doctor profile for the logged-in Clinic Portal clinician."""

from __future__ import annotations

import hashlib
from html import escape

import streamlit as st

from utils.avatar import make_circular_avatar_data_url
from utils.db import (
    get_clinic_schedule,
    get_clinician_dashboard_stats,
    get_clinician_profile,
    get_clinician_recent_activity,
    log_clinician_activity,
    save_clinician_profile,
)
from utils.i18n import LANGUAGE_OPTIONS, normalize_language, t

_PROFILE_CSS = """
<style>
.dp-page {
    animation: dp-fade-up 0.34s cubic-bezier(0.4, 0, 0.2, 1) both;
    max-width: 1120px;
}
.dp-page-title {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 36px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.15;
    color: var(--ink-primary, #13203A);
    margin: 0 0 0.35rem 0;
}
.dp-page-subtitle {
    font-size: 14px;
    line-height: 1.55;
    color: var(--ink-muted, #7A879C);
    margin: 0 0 1.75rem 0;
}
.dp-section-title {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.015em;
    color: var(--ink-primary, #13203A);
    margin: 0 0 0.35rem 0;
}
.dp-section-caption {
    font-size: 13px;
    line-height: 1.5;
    color: var(--ink-muted, #7A879C);
    margin: 0 0 1.1rem 0;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(20, 40, 65, 0.10) !important;
    border-radius: 18px !important;
    box-shadow: 0 2px 10px rgba(20, 40, 65, 0.05) !important;
    padding: 0.35rem 0.15rem !important;
    margin-bottom: 0.35rem;
    animation: dp-fade-up 0.34s cubic-bezier(0.4, 0, 0.2, 1) both;
}
.dp-hero {
    display: grid;
    grid-template-columns: 128px 1fr;
    gap: 1.5rem;
    align-items: start;
    padding: 0.35rem 0.25rem 0.15rem;
}
.dp-avatar-wrap {
    position: relative;
    width: 128px;
    height: 128px;
}
.dp-avatar, .dp-avatar-img {
    width: 128px;
    height: 128px;
    border-radius: 50%;
    flex-shrink: 0;
    transition: transform 0.28s ease;
}
.dp-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(145deg, #4A7BA6 0%, #1C3D5A 100%);
    color: white;
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    box-shadow: 0 8px 20px rgba(28, 61, 90, 0.18);
}
.dp-avatar-img {
    object-fit: cover;
    border: 3px solid rgba(74, 123, 166, 0.22);
    box-shadow: 0 8px 20px rgba(28, 61, 90, 0.12);
}
.dp-avatar-wrap:hover .dp-avatar,
.dp-avatar-wrap:hover .dp-avatar-img { transform: scale(1.02); }
/* Camera-icon file uploader overlaid on the avatar (LinkedIn-style). */
.st-key-dp_avatar_block {
    position: relative !important;
    width: 128px !important;
    min-height: 128px !important;
}
.st-key-dp_avatar_block > div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
.st-key-dp_camera_upload {
    position: absolute !important;
    right: -2px !important;
    bottom: 2px !important;
    width: 40px !important;
    min-width: 40px !important;
    z-index: 8 !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploader"] {
    width: 40px !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] {
    min-height: 36px !important;
    height: 36px !important;
    width: 36px !important;
    max-width: 36px !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 50% !important;
    border: 2.5px solid #FFFFFF !important;
    background: #4A7BA6 !important;
    box-shadow: 0 4px 12px rgba(28, 61, 90, 0.30) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: transform 0.2s ease, filter 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease !important;
    overflow: hidden !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"]:hover {
    transform: scale(1.1) !important;
    filter: brightness(1.12);
    background: #5B8CB5 !important;
    box-shadow: 0 6px 16px rgba(28, 61, 90, 0.36) !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"]:active {
    transform: scale(0.94) !important;
    filter: brightness(0.98);
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] > *,
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzoneInstructions"],
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] button,
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] svg,
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] small,
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] span,
.st-key-dp_camera_upload [data-testid="stFileUploaderFileName"],
.st-key-dp_camera_upload [data-testid="stFileUploaderFile"],
.st-key-dp_camera_upload [data-testid="stMarkdownContainer"],
.st-key-dp_camera_upload label {
    display: none !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] input[type="file"] {
    display: block !important;
    opacity: 0 !important;
    position: absolute !important;
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    cursor: pointer !important;
    z-index: 2 !important;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"]::after {
    content: "";
    width: 16px;
    height: 16px;
    display: block;
    background-color: #FFFFFF;
    pointer-events: none;
    position: relative;
    z-index: 1;
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M9 3.5a1 1 0 0 1 .8-.4h4.4a1 1 0 0 1 .8.4l.9 1.1H19a2.5 2.5 0 0 1 2.5 2.5v10A2.5 2.5 0 0 1 19 19.6H5A2.5 2.5 0 0 1 2.5 17.1v-10A2.5 2.5 0 0 1 5 4.6h2.1L9 3.5Zm3 13.1a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Zm0-1.8a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8Z'/%3E%3C/svg%3E") center / contain no-repeat;
    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='black'%3E%3Cpath d='M9 3.5a1 1 0 0 1 .8-.4h4.4a1 1 0 0 1 .8.4l.9 1.1H19a2.5 2.5 0 0 1 2.5 2.5v10A2.5 2.5 0 0 1 19 19.6H5A2.5 2.5 0 0 1 2.5 17.1v-10A2.5 2.5 0 0 1 5 4.6h2.1L9 3.5Zm3 13.1a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Zm0-1.8a2.4 2.4 0 1 1 0-4.8 2.4 2.4 0 0 1 0 4.8Z'/%3E%3C/svg%3E") center / contain no-repeat;
}
.st-key-dp_camera_upload [data-testid="stFileUploaderDropzone"] section {
    padding: 0 !important;
    min-height: 0 !important;
}
.dp-name {
    font-family: var(--font-serif, Georgia, serif);
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 0 0 0.45rem 0;
    color: var(--ink-primary, #13203A);
}
.dp-role {
    font-size: 16px;
    font-weight: 600;
    color: var(--ink-primary, #13203A);
    margin: 0 0 0.2rem 0;
    line-height: 1.4;
}
.dp-org {
    font-size: 15px;
    color: var(--ink-secondary, #445068);
    margin: 0 0 0.95rem 0;
    line-height: 1.45;
}
.dp-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.55rem 1.25rem;
    padding-top: 0.85rem;
    border-top: 1px solid rgba(20, 40, 65, 0.08);
}
.dp-detail-label {
    display: block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-muted, #7A879C);
    margin-bottom: 0.15rem;
}
.dp-detail-value {
    font-size: 14px;
    color: var(--ink-secondary, #445068);
    line-height: 1.4;
}
.dp-stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
}
.dp-stat {
    background: #F8FAFC;
    border: 1px solid rgba(20, 40, 65, 0.08);
    border-radius: 14px;
    padding: 1.05rem 1.1rem;
    text-align: left;
    animation: dp-fade-up 0.36s cubic-bezier(0.4, 0, 0.2, 1) both;
}
.dp-stat .label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--ink-muted, #7A879C);
    font-weight: 700;
    line-height: 1.3;
}
.dp-stat .value {
    font-size: 32px;
    font-weight: 800;
    color: var(--ink-primary, #13203A);
    margin-top: 0.35rem;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.dp-stat.ai .value { color: #6A4C93; }
.dp-stat.alert .value { color: #B8892B; }
.dp-stat.risk .value { color: #B33A3A; }
.dp-stat.blue .value { color: #3A6488; }
.dp-row {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 1rem;
    align-items: baseline;
    padding: 0.85rem 0;
    border-bottom: 1px solid rgba(20, 40, 65, 0.07);
}
.dp-row:last-child { border-bottom: none; }
.dp-row .left {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--ink-muted, #7A879C);
    text-transform: uppercase;
}
.dp-row .right {
    font-size: 15px;
    color: var(--ink-primary, #13203A);
    line-height: 1.45;
}
.dp-bio {
    margin-top: 0.85rem;
    padding-top: 0.85rem;
    border-top: 1px solid rgba(20, 40, 65, 0.07);
}
.dp-bio-label {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--ink-muted, #7A879C);
    margin-bottom: 0.35rem;
}
.dp-bio-body {
    font-size: 15px;
    line-height: 1.6;
    color: var(--ink-secondary, #445068);
}
.dp-appt {
    display: grid;
    grid-template-columns: 92px 1fr auto;
    gap: 0.9rem;
    align-items: center;
    padding: 0.9rem 0.1rem;
    border-bottom: 1px solid rgba(20, 40, 65, 0.07);
    animation: dp-fade-up 0.3s ease both;
}
.dp-appt:last-child { border-bottom: none; }
.dp-appt .time {
    font-family: var(--font-mono, monospace);
    font-size: 15px;
    font-weight: 700;
    color: #3A6488;
    line-height: 1.25;
}
.dp-appt .date {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: #7A879C;
    margin-top: 0.15rem;
}
.dp-appt .patient {
    font-size: 15px;
    font-weight: 700;
    color: var(--ink-primary, #13203A);
}
.dp-appt .visit {
    font-size: 13px;
    color: var(--ink-secondary, #445068);
    margin-top: 0.15rem;
}
.dp-appt .status {
    font-size: 12px;
    font-weight: 700;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
}
.dp-appt .status.today { background: rgba(184, 137, 43, 0.14); color: #8A6A12; }
.dp-appt .status.upcoming { background: rgba(74, 123, 166, 0.12); color: #3A6488; }
.dp-activity {
    padding: 0.85rem 0;
    border-bottom: 1px solid rgba(20, 40, 65, 0.07);
}
.dp-activity:last-child { border-bottom: none; }
.dp-activity .action {
    font-size: 15px;
    font-weight: 700;
    color: var(--ink-primary, #13203A);
    line-height: 1.35;
}
.dp-activity .detail {
    color: var(--ink-secondary, #445068);
    font-size: 13px;
    margin-top: 0.2rem;
    line-height: 1.45;
}
.dp-activity .ts {
    color: var(--ink-muted, #7A879C);
    font-size: 12px;
    font-family: var(--font-mono, monospace);
    margin-top: 0.3rem;
}
.dp-spacer { height: 0.85rem; }
.dp-toast {
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
    border: 1px solid rgba(30, 122, 76, 0.22);
    box-shadow: 0 8px 24px rgba(20, 40, 65, 0.14);
    font-weight: 700;
    font-size: 14px;
    animation: dp-toast-in 0.3s ease both, dp-toast-out 0.35s ease 2.4s forwards;
}
.dp-toast-check {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #1E7A4C;
    color: white;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
}
@keyframes dp-fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes dp-toast-in {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes dp-toast-out {
    from { opacity: 1; }
    to { opacity: 0; visibility: hidden; }
}
.st-key-dp_save_btn button,
.st-key-dp_edit_btn button,
.st-key-dp_cancel_btn button,
.st-key-dp_remove_photo_btn button {
    transition: transform 0.25s ease, box-shadow 0.25s ease !important;
}
.st-key-dp_save_btn button:hover,
.st-key-dp_edit_btn button:hover,
.st-key-dp_cancel_btn button:hover,
.st-key-dp_remove_photo_btn button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(20, 40, 65, 0.16);
}
@media (max-width: 900px) {
    .dp-page-title { font-size: 30px; }
    .dp-name { font-size: 26px; }
    .dp-hero { grid-template-columns: 96px 1fr; gap: 1rem; }
    .dp-avatar-wrap, .st-key-dp_avatar_block { width: 96px !important; min-height: 96px !important; }
    .dp-avatar, .dp-avatar-img { width: 96px; height: 96px; font-size: 1.6rem; }
    .dp-details { grid-template-columns: 1fr; }
    .dp-stats-grid { grid-template-columns: 1fr; }
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


def _render_stat(label: str, value: int, variant: str = "") -> None:
    cls = f"dp-stat {variant}".strip()
    st.markdown(
        f'<div class="{cls}"><div class="label">{escape(label)}</div>'
        f'<div class="value" data-count="{int(value)}">{int(value):,}</div></div>',
        unsafe_allow_html=True,
    )


def _section_header(title: str, caption: str = "") -> None:
    caption_html = f'<p class="dp-section-caption">{escape(caption)}</p>' if caption else ""
    st.markdown(
        f'<h2 class="dp-section-title">{escape(title)}</h2>{caption_html}',
        unsafe_allow_html=True,
    )


def _format_timestamp(ts: str) -> str:
    if not ts:
        return ""
    return ts.replace("T", " ")[:19]


username = st.session_state.get("clinic_user")
if not st.session_state.get("clinic_authenticated") or not username:
    st.warning(t("login_required_profile"))
    st.stop()

account = get_clinician_profile(username)
if not account:
    st.error(t("account_load_error"))
    st.stop()

profile = account["profile"]
stats = get_clinician_dashboard_stats(username)
schedule = get_clinic_schedule()
activity = get_clinician_recent_activity(username)
doctor_name = profile.get("full_name") or account["display_name"]
st.session_state.setdefault("dp_last_photo_digest", None)

st.markdown(_PROFILE_CSS, unsafe_allow_html=True)
st.markdown("<div class='dp-page'>", unsafe_allow_html=True)
st.markdown(f"<h1 class='dp-page-title'>{escape(t('doctor_profile'))}</h1>", unsafe_allow_html=True)
st.markdown(
    f"<p class='dp-page-subtitle'>{escape(t('doctor_profile_subtitle', name=doctor_name, username=account['username']))}</p>",
    unsafe_allow_html=True,
)

edit_mode = st.session_state.get("dp_edit_mode", False)

# ---- Large profile card + statistics ----
left, right = st.columns([1.45, 1], gap="large")

with left:
    with st.container(border=True):
        hero_avatar, hero_info = st.columns([0.95, 2.2], gap="large")

        with hero_avatar:
            with st.container(key="dp_avatar_block"):
                avatar_inner = (
                    f'<img class="dp-avatar-img" src="{escape(profile.get("photo_data_url") or "", quote=True)}" '
                    f'alt="Doctor profile photo" />'
                    if str(profile.get("photo_data_url") or "").startswith("data:image")
                    else f'<div class="dp-avatar">{escape(_initials(doctor_name))}</div>'
                )
                st.markdown(
                    f'<div class="dp-avatar-wrap">{avatar_inner}</div>',
                    unsafe_allow_html=True,
                )
                photo_upload = st.file_uploader(
                    t("change_photo"),
                    type=["png", "jpg", "jpeg", "webp"],
                    key="dp_camera_upload",
                    label_visibility="collapsed",
                    accept_multiple_files=False,
                )

            if photo_upload is not None:
                digest = hashlib.sha1(photo_upload.getvalue()).hexdigest()
                if st.session_state.get("dp_last_photo_digest") != digest:
                    try:
                        profile["photo_data_url"] = make_circular_avatar_data_url(photo_upload.getvalue())
                        if save_clinician_profile(username, profile):
                            log_clinician_activity(username, "Updated profile photo", "Circular avatar saved")
                            st.session_state.dp_last_photo_digest = digest
                            st.session_state.dp_photo_success = True
                            st.rerun()
                        st.error(t("could_not_save_profile"))
                    except Exception:
                        st.error(t("could_not_save_profile"))

            if str(profile.get("photo_data_url") or "").startswith("data:image"):
                if st.button(t("remove_photo"), key="dp_remove_photo_btn", use_container_width=True):
                    profile["photo_data_url"] = ""
                    if save_clinician_profile(username, profile):
                        log_clinician_activity(username, "Removed profile photo", "Using initials avatar")
                        st.session_state.dp_last_photo_digest = None
                        st.session_state.dp_photo_success = True
                        st.rerun()

        with hero_info:
            st.markdown(
                f"""
                <p class="dp-name">{escape(doctor_name)}</p>
                <p class="dp-role">{escape(profile.get('title') or t('physician'))}</p>
                <p class="dp-org">{escape(profile.get('department') or '—')} · {escape(profile.get('hospital_name') or '—')}</p>
                <div class="dp-details">
                  <div>
                    <span class="dp-detail-label">{escape(t('employee_id'))}</span>
                    <span class="dp-detail-value">{escape(profile.get('employee_id') or '—')}</span>
                  </div>
                  <div>
                    <span class="dp-detail-label">{escape(t('experience'))}</span>
                    <span class="dp-detail-value">{int(profile.get('years_experience') or 0)} {escape(t('years'))}</span>
                  </div>
                  <div>
                    <span class="dp-detail-label">{escape(t('email'))}</span>
                    <span class="dp-detail-value">{escape(profile.get('email') or t('not_set'))}</span>
                  </div>
                  <div>
                    <span class="dp-detail-label">{escape(t('phone'))}</span>
                    <span class="dp-detail-value">{escape(profile.get('phone') or t('not_set'))}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div class='dp-spacer'></div>", unsafe_allow_html=True)
        if st.button(t("edit_profile"), key="dp_edit_btn", use_container_width=True):
            st.session_state.dp_edit_mode = not edit_mode
            st.rerun()

with right:
    with st.container(border=True):
        _section_header(t("quick_statistics"), t("quick_statistics_caption"))
        st.markdown('<div class="dp-stats-grid">', unsafe_allow_html=True)
        _render_stat(t("stat_patients_today"), stats["patients_seen_today"], "blue")
        _render_stat(t("stat_total_patients"), stats["total_patients"])
        _render_stat(t("stat_ai_reports"), stats["ai_reports_reviewed"], "ai")
        _render_stat(t("stat_upcoming"), stats["upcoming_appointments"], "alert")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='dp-spacer'></div>", unsafe_allow_html=True)
        _render_stat(t("stat_high_risk"), stats["high_risk_cases"], "risk")

st.markdown("<div class='dp-spacer'></div>", unsafe_allow_html=True)

# ---- Professional information (editable, includes Preferred Language) ----
lang_codes = [code for code, _ in LANGUAGE_OPTIONS]
lang_labels = {code: label for code, label in LANGUAGE_OPTIONS}

with st.container(border=True):
    _section_header(t("professional_information"), t("professional_caption"))
    c1, c2 = st.columns(2, gap="large")
    with c1:
        profile["full_name"] = st.text_input(t("full_name"), profile.get("full_name", ""), key="dp_full_name")
        profile["title"] = st.text_input(t("professional_title"), profile.get("title", ""), key="dp_title")
        profile["department"] = st.text_input(t("department"), profile.get("department", ""), key="dp_department")
        profile["email"] = st.text_input(t("contact_email"), profile.get("email", ""), key="dp_email")
        profile["phone"] = st.text_input(t("phone_number"), profile.get("phone", ""), key="dp_phone")
    with c2:
        profile["years_experience"] = int(
            st.number_input(
                t("years_experience"),
                min_value=0,
                max_value=60,
                value=int(profile.get("years_experience") or 0),
                step=1,
                key="dp_years_experience",
            )
        )
        profile["specialty"] = st.text_input(t("specialty"), profile.get("specialty", ""), key="dp_specialty")
        profile["languages"] = st.text_input(
            t("languages_spoken"),
            profile.get("languages", ""),
            key="dp_languages_spoken",
        )
        current_lang = normalize_language(profile.get("preferred_language"))
        profile["preferred_language"] = st.selectbox(
            t("preferred_language"),
            lang_codes,
            index=lang_codes.index(current_lang),
            format_func=lambda code: lang_labels[code],
            help=t("preferred_language_help"),
            key="dp_preferred_language",
        )

    save_col, _ = st.columns([1, 3])
    with save_col:
        if st.button(t("save_changes"), type="primary", key="dp_save_btn", use_container_width=True):
            with st.spinner(t("saving_profile")):
                ok = save_clinician_profile(username, profile)
            if ok:
                log_clinician_activity(username, "Updated professional information", "Profile and language preference saved")
                st.session_state.clinic_display_name = profile.get("full_name") or account["display_name"]
                # Persist language on the account; apply after the next page refresh / login.
                st.session_state.pop("_language_loaded_for", None)
                st.session_state.dp_save_success = True
                st.rerun()
            else:
                st.error(t("could_not_save_profile"))

st.markdown("<div class='dp-spacer'></div>", unsafe_allow_html=True)

# ---- Schedule + Recent activity ----
sched_col, act_col = st.columns(2, gap="large")

with sched_col:
    with st.container(border=True):
        _section_header(t("todays_schedule"), t("schedule_caption"))
        if not schedule:
            st.info(t("no_upcoming_appointments"))
        else:
            for item in schedule:
                status_key = "status_today" if item["status"] == "Today" else "status_upcoming"
                status_cls = "today" if item["status"] == "Today" else "upcoming"
                st.markdown(
                    f"<div class='dp-appt'>"
                    f"<div class='time'>{escape(item['time'])}"
                    f"<span class='date'>{escape(item['date'])}</span></div>"
                    f"<div><div class='patient'>{escape(item['patient_name'])}</div>"
                    f"<div class='visit'>{escape(item['visit_type'])} · {escape(item['patient_id'])}</div></div>"
                    f"<div class='status {status_cls}'>{escape(t(status_key))}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

with act_col:
    with st.container(border=True):
        _section_header(t("recent_activity"), t("activity_caption"))
        if not activity:
            st.info(t("no_recent_activity"))
        else:
            for event in activity:
                st.markdown(
                    f"<div class='dp-activity'>"
                    f"<div class='action'>{escape(event['action'])}</div>"
                    f"<div class='detail'>{escape(event.get('detail') or '')}</div>"
                    f"<div class='ts'>{escape(_format_timestamp(event.get('timestamp') or ''))}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

st.markdown("<div class='dp-spacer'></div>", unsafe_allow_html=True)

# ---- Additional account settings (optional) ----
if st.session_state.get("dp_edit_mode", False):
    with st.container(border=True):
        _section_header(t("account_settings"), t("account_settings_caption"))

        e1, e2 = st.columns(2, gap="large")
        with e1:
            profile["hospital_name"] = st.text_input(t("hospital_name"), profile.get("hospital_name", ""))
            profile["certifications"] = st.text_input(t("certifications"), profile.get("certifications", ""))
            profile["license_number"] = st.text_input(t("medical_license"), profile.get("license_number", ""))
            profile["education"] = st.text_input(t("education"), profile.get("education", ""))
        with e2:
            profile["research_interests"] = st.text_input(
                t("research_interests"),
                profile.get("research_interests", ""),
            )
            theme_options = ["system", "light", "dark"]
            theme_labels = {
                "system": t("theme_system"),
                "light": "Light",
                "dark": "Dark",
            }
            current_theme = (
                profile.get("theme_preference")
                if profile.get("theme_preference") in theme_options
                else "system"
            )
            profile["theme_preference"] = st.selectbox(
                t("theme_preference"),
                theme_options,
                index=theme_options.index(current_theme),
                format_func=lambda value: theme_labels[value],
                help=t("theme_future"),
            )

        profile["biography"] = st.text_area(t("biography"), profile.get("biography", ""), height=110)

        st.markdown(f"**{t('notification_preferences')}**")
        n1, n2 = st.columns(2)
        notes = profile.setdefault("notifications", {})
        with n1:
            notes["email_alerts"] = st.toggle(t("email_alerts"), value=bool(notes.get("email_alerts", True)))
            notes["high_risk_alerts"] = st.toggle(
                t("high_risk_alerts"),
                value=bool(notes.get("high_risk_alerts", True)),
            )
        with n2:
            notes["appointment_reminders"] = st.toggle(
                t("appointment_reminders"),
                value=bool(notes.get("appointment_reminders", True)),
            )
            notes["ai_summary_alerts"] = st.toggle(
                t("ai_summary_alerts"),
                value=bool(notes.get("ai_summary_alerts", True)),
            )
        profile["notifications"] = notes

        save_col, cancel_col, _ = st.columns([1, 1, 2])
        with save_col:
            if st.button(t("save_changes"), type="primary", key="dp_save_extra_btn", use_container_width=True):
                with st.spinner(t("saving_profile")):
                    ok = save_clinician_profile(username, profile)
                if ok:
                    log_clinician_activity(username, "Updated doctor profile", "Account settings saved")
                    st.session_state.clinic_display_name = profile.get("full_name") or account["display_name"]
                    st.session_state.dp_edit_mode = False
                    st.session_state.dp_save_success = True
                    st.rerun()
                else:
                    st.error(t("could_not_save_profile"))
        with cancel_col:
            if st.button(t("cancel"), key="dp_cancel_btn", use_container_width=True):
                st.session_state.dp_edit_mode = False
                st.rerun()

if st.session_state.pop("dp_photo_success", False):
    toast_text = t("photo_updated")
elif st.session_state.pop("dp_save_success", False):
    toast_text = t("profile_updated")
else:
    toast_text = None

if toast_text:
    st.markdown(
        f'<div class="dp-toast" role="status">'
        f'<span class="dp-toast-check">✓</span>'
        f"<span>{escape(toast_text)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <script>
    (function () {
      const nodes = window.parent.document.querySelectorAll('.dp-stat .value[data-count]');
      nodes.forEach((el, idx) => {
        const target = Number(el.getAttribute('data-count') || 0);
        if (!Number.isFinite(target)) return;
        let current = 0;
        const steps = 18;
        const increment = target / steps;
        el.textContent = '0';
        const timer = setInterval(() => {
          current += increment;
          if (current >= target) {
            el.textContent = target.toLocaleString();
            clearInterval(timer);
          } else {
            el.textContent = Math.round(current).toLocaleString();
          }
        }, 16 + idx);
      });
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
