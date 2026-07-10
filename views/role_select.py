import streamlit as st

st.markdown(
    """
    <style>
    .st-key-hero_section {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .st-key-hero_section div[data-testid="stMarkdownContainer"] {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .hero-title {
        font-size: 84px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #000000;
        line-height: 1.05;
        margin-bottom: 16px;
        text-align: center;
        width: 100%;
    }
    .hero-subtitle {
        font-size: 21px;
        color: #3D3D42;
        max-width: 640px;
        text-align: center;
    }
    .scroll-hint {
        margin-top: 56px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: #63636B;
        text-align: center;
        width: 100%;
        animation: bounce 2s ease-in-out infinite;
    }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); opacity: 0.6; }
        50% { transform: translateY(10px); opacity: 1; }
    }

    /* "About" rendered as a plain clickable word instead of a filled
       button -- overrides the app-wide button styling for this key only. */
    .st-key-about_link {
        display: flex;
        justify-content: center;
        width: 100%;
    }
    .st-key-about_link button {
        background: transparent !important;
        border: none !important;
        width: auto !important;
        height: auto !important;
        padding: 2px 6px !important;
        box-shadow: none !important;
        margin-top: 18px;
    }
    .st-key-about_link button p, .st-key-about_link button span, .st-key-about_link button div {
        color: var(--ink-muted) !important;
        text-decoration: underline;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    .st-key-about_link button:hover p, .st-key-about_link button:hover span, .st-key-about_link button:hover div {
        color: var(--brand) !important;
    }

    /* Options section also fills the viewport (plus a bit extra for more
       breathing room / scroll distance before the cards settle), and
       centers its content so it reads as its own "page" once scrolled
       into view. */
    .st-key-options_section {
        min-height: 118vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    /* Equal card heights + pin the CTA to the bottom of each card,
       regardless of the description text wrapping to a different number
       of lines -- otherwise the two buttons don't line up. */
    .st-key-patient_card, .st-key-clinic_card {
        display: flex !important;
        flex-direction: column;
        min-height: 260px;
    }
    .st-key-patient_cta, .st-key-clinic_cta {
        margin-top: auto;
        padding-top: 12px;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(240px) scale(0.82);
            filter: blur(10px);
        }
        55% {
            filter: blur(0);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
            filter: blur(0);
        }
    }

    /* Scroll-driven reveal for the two role cards. "entry" ties to the
       element's OWN height crossing the viewport edge, which for a ~350px
       card resolves almost instantly -- too fast. "cover" spans the
       element's full pass through the viewport (~element height +
       viewport height), so a wide slice of that gives a slow,
       scroll-distance-driven effect instead of a quick pop-in. The two
       cards use offset ranges (not animation-delay, whose semantics get
       murky under a scroll timeline) so Clinic Staff visibly trails
       Patient rather than arriving almost together. Falls back to a
       plain fade-in on load for browsers without animation-timeline
       support (Firefox / older Safari) so the cards are never stuck
       invisible. */
    .st-key-patient_card, .st-key-clinic_card {
        opacity: 0;
        animation: fadeInUp 2.2s cubic-bezier(0.16, 1, 0.3, 1) both;
        animation-timeline: view();
    }
    .st-key-patient_card { animation-range: cover 0% cover 85%; }
    .st-key-clinic_card { animation-range: cover 12% cover 97%; }

    @supports not (animation-timeline: view()) {
        .st-key-patient_card, .st-key-clinic_card {
            opacity: 1;
            animation: fadeInUp 1s ease-out both;
        }
        .st-key-patient_card { animation-delay: 0.1s; }
        .st-key-clinic_card { animation-delay: 0.3s; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="hero_section"):
    st.markdown("<div class='hero-title'>BrainGuard AI</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-subtitle'>AI-Powered Dementia Risk Assessment &amp; Patient Management System</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='scroll-hint'>Scroll down to continue &#8595;</div>", unsafe_allow_html=True)

    def _open_about():
        st.session_state.show_about = True

    st.button("About", key="about_link", on_click=_open_about)

with st.container(key="options_section"):
    st.write("Please select how you'd like to continue:")
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True, key="patient_card"):
            st.markdown("<span class='accent-bar accent-bar-blue'></span>", unsafe_allow_html=True)
            st.subheader("Patient")
            st.markdown("<span class='tag tag-yellow'>No sign-in required</span>", unsafe_allow_html=True)
            st.write("Check your own modifiable dementia risk factors.")
            if st.button("Continue as Patient", type="primary", width="stretch", key="patient_cta"):
                st.session_state.role = "patient"
                st.rerun()

    with col2:
        with st.container(border=True, key="clinic_card"):
            st.markdown("<span class='accent-bar accent-bar-violet'></span>", unsafe_allow_html=True)
            st.subheader("Clinic Staff")
            st.markdown("<span class='tag tag-yellow'>Full diagnostics</span>", unsafe_allow_html=True)
            st.write("Access the full patient management and diagnostics dashboard.")
            if st.button("Continue as Clinic Staff", type="primary", width="stretch", key="clinic_cta"):
                st.session_state.role = "clinic"
                st.rerun()
