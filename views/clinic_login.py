import os

import streamlit as st

from utils.db import create_clinician, reset_clinician_password, verify_clinician

# Shared invite code required to create a clinician account, so a public
# deployment can't have anyone self-register into the full patient dashboard.
# Read from st.secrets first (set a private one per deployment), then an env
# var, then a documented default so local dev still works out of the box.
_DEFAULT_SIGNUP_CODE = "6"


def _clinic_signup_code() -> str:
    try:
        value = st.secrets.get("CLINIC_SIGNUP_CODE")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return (os.getenv("CLINIC_SIGNUP_CODE") or _DEFAULT_SIGNUP_CODE).strip()


st.markdown("<div class='bg-section'>Clinic Access</div>", unsafe_allow_html=True)
st.warning(
    "**Demonstration access only.** This clinic portal is a prototype, not a "
    "production clinical system. Do not enter real patient names, contact "
    "details, or other protected health information (PHI) anywhere in this "
    "portal -- use fictitious or test data only."
)

tab_login, tab_register, tab_reset = st.tabs(["Log In", "Create Account", "Reset Password"])

with tab_login:
    st.write("Log in with your clinician account to continue.")
    login_username = st.text_input("Username", key="login_username")
    login_password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Log In", type="primary", width="stretch"):
            clinician = verify_clinician(login_username, login_password)
            if clinician:
                st.session_state.clinic_authenticated = True
                st.session_state.clinic_user = clinician["username"]
                st.session_state.clinic_display_name = clinician["display_name"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with col2:
        if st.button("Back", width="stretch", key="login_back"):
            st.session_state.role = None
            st.rerun()

with tab_register:
    st.write("New clinicians can create an account here.")
    st.caption(
        "Account creation requires a clinic invite code. If you don't have one, "
        "ask whoever administers this deployment."
    )
    reg_signup_code = st.text_input("Clinic invite code", type="password", key="reg_signup_code")
    reg_username = st.text_input("Choose a username", key="reg_username")
    reg_display_name = st.text_input("Display name", key="reg_display_name")
    reg_password = st.text_input("Choose a password", type="password", key="reg_password")
    reg_password_confirm = st.text_input("Confirm password", type="password", key="reg_password_confirm")

    if st.button("Create Account", type="primary", key="reg_submit"):
        if not reg_signup_code.strip():
            st.error("A clinic invite code is required to create an account.")
        elif reg_signup_code.strip() != _clinic_signup_code():
            st.error("That clinic invite code is not valid.")
        elif not reg_username.strip() or not reg_password:
            st.error("Username and password are required.")
        elif len(reg_password) < 8:
            st.error("Password must be at least 8 characters.")
        elif reg_password != reg_password_confirm:
            st.error("Passwords don't match.")
        else:
            created = create_clinician(reg_username.strip(), reg_password, reg_display_name.strip())
            if created:
                st.success("Account created — you can now log in from the Log In tab.")
            else:
                st.error("That username is already taken.")

with tab_reset:
    st.write("Forgot your password? Another clinician on your team can reset it for you.")
    st.caption(
        "No email system is set up for this prototype, so resets are peer-verified: "
        "a different, currently-valid clinician account authorizes the change."
    )

    target_username = st.text_input("Username to reset", key="reset_target_username")
    new_reset_password = st.text_input("New password", type="password", key="reset_new_password")
    new_reset_password_confirm = st.text_input(
        "Confirm new password", type="password", key="reset_new_password_confirm"
    )

    st.markdown("**Authorizing clinician** (a different, existing account)")
    auth_col1, auth_col2 = st.columns(2)
    with auth_col1:
        authorizer_username = st.text_input("Authorizer's username", key="reset_authorizer_username")
    with auth_col2:
        authorizer_password = st.text_input(
            "Authorizer's password", type="password", key="reset_authorizer_password"
        )

    if st.button("Reset Password", type="primary", key="reset_submit"):
        if not target_username.strip() or not new_reset_password:
            st.error("Username and new password are required.")
        elif len(new_reset_password) < 8:
            st.error("New password must be at least 8 characters.")
        elif new_reset_password != new_reset_password_confirm:
            st.error("New passwords don't match.")
        elif target_username.strip().lower() == authorizer_username.strip().lower():
            st.error("The authorizing account must be a different clinician than the one being reset.")
        elif verify_clinician(authorizer_username, authorizer_password) is None:
            st.error("Authorizing clinician's credentials are invalid.")
        else:
            reset = reset_clinician_password(target_username.strip(), new_reset_password)
            if reset:
                st.success(f"Password reset for '{target_username.strip()}'. You can now log in from the Log In tab.")
            else:
                st.error(f"No clinician account found with username '{target_username.strip()}'.")
