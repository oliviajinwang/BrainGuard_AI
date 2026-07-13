import streamlit as st

st.markdown(
    """
    <style>
    .st-key-hero_section {
        min-height: 92vh;
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
    .hero-eyebrow {
        font-family: var(--font-mono);
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--brand-blue);
        margin-bottom: 20px;
        text-align: center;
        width: 100%;
    }
    .hero-title {
        font-family: var(--font-serif);
        font-size: 88px;
        font-weight: 500;
        letter-spacing: -0.01em;
        color: var(--ink-primary);
        line-height: 1.05;
        margin-bottom: 20px;
        text-align: center;
        width: 100%;
    }
    .hero-subtitle {
        font-size: 21px;
        color: var(--ink-secondary);
        max-width: 640px;
        text-align: center;
    }

    /* At phone widths, 88px wraps "BrainGuard AI" mid-word ("BrainG" /
       "uard AI") since the word itself is wider than the viewport. */
    @media (max-width: 480px) {
        .hero-title { font-size: 48px; }
        .hero-subtitle { font-size: 17px; }
        .hero-eyebrow { font-size: 11px; }
    }

    /* Centers the "Continue" button instead of letting it sit flush-left
       like a normal block-level st.button. st.container() renders as a
       stVerticalBlock, which Streamlit's own base CSS already sets to
       flex-direction: column -- so centering its child horizontally needs
       align-items (the cross-axis), not justify-content (which would
       center along the vertical main axis instead and do nothing visible
       here). */
    .st-key-continue_section {
        display: flex;
        align-items: center;
        width: 100%;
        margin-top: 32px;
    }

    /* One-shot entrance animation on page load -- plain document-timeline
       (no animation-timeline: view()), so it plays once when the section
       mounts and never re-triggers on scroll. */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .st-key-mission_section, .st-key-mission_stat_card,
    .st-key-vision_card, .st-key-goal_card, .pull-quote {
        animation: fadeInUp 0.7s ease-out both;
    }
    .st-key-mission_stat_card { animation-delay: 0.1s; }
    .st-key-vision_card { animation-delay: 0.1s; }
    .st-key-goal_card { animation-delay: 0.22s; }
    .pull-quote { animation-delay: 0.32s; }

    /* Stat callout -- the one hard number we actually have (~40%),
       presented as its own card rather than buried in a paragraph. */
    .st-key-mission_stat_card {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        height: 100%;
        min-height: 200px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .st-key-mission_stat_card:hover {
        transform: translateY(-6px);
        box-shadow: var(--shadow-md);
    }
    .stat-number {
        font-family: var(--font-serif);
        font-size: 64px;
        font-weight: 600;
        color: var(--brand);
        line-height: 1;
        margin-bottom: 10px;
    }
    .stat-caption {
        font-size: 14px;
        color: var(--ink-secondary);
        line-height: 1.5;
        max-width: 220px;
    }

    /* Vision / Goal cards -- same card language as the role-select
       cards (accent-bar + bordered container), with a hover-lift. */
    .st-key-vision_card, .st-key-goal_card {
        height: 100%;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .st-key-vision_card:hover, .st-key-goal_card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-md);
    }

    /* "The Core Question" as a pull-quote instead of a plain info box. */
    .pull-quote {
        position: relative;
        font-family: var(--font-serif);
        font-style: italic;
        font-size: 21px;
        line-height: 1.55;
        color: var(--ink-primary);
        padding: 10px 20px 10px 40px;
        border-left: 3px solid var(--brand-blue);
        margin: 12px 0 20px 0;
    }
    .pull-quote::before {
        content: "\\201C";
        position: absolute;
        left: 4px;
        top: -8px;
        font-size: 56px;
        font-family: var(--font-serif);
        color: var(--brand-blue);
        opacity: 0.35;
        line-height: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _go_to_role_select():
    st.session_state.show_role_select = True


with st.container(key="hero_section"):
    st.markdown("<div class='hero-eyebrow'>Explainable AI &middot; Dementia Screening</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-title'>BrainGuard AI</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-subtitle'>AI-Powered Dementia Risk Assessment &amp; Patient Management System</div>",
        unsafe_allow_html=True,
    )
    with st.container(key="continue_section"):
        st.button("Continue →", on_click=_go_to_role_select, type="primary")

with st.container(key="mission_section"):
    st.markdown("<div class='bg-section'>Our Mission</div>", unsafe_allow_html=True)

    mcol1, mcol2 = st.columns([3, 2], gap="large")
    with mcol1:
        st.write(
            "BrainGuard AI is an educational and clinical decision-support prototype "
            "that estimates dementia-related risk from lifestyle, cognitive, and "
            "structural factors, and explains which factors influenced each estimate. "
            "It is not a diagnosis, a medical device, or a substitute for professional "
            "medical evaluation."
        )
        st.write(
            "According to research, about 40% of dementia cases could have been prevented "
            "or slowed by modifying lifestyle factors, meaning that changes in small, "
            "everyday habits can meaningfully affect long-term risk. By surfacing "
            "modifiable, model-associated factors early and explaining them clearly, we "
            "hope to support more informed conversations between patients and their care "
            "teams -- though model associations do not prove that changing any one factor "
            "will change an individual's outcome."
        )
    with mcol2:
        with st.container(border=True, key="mission_stat_card"):
            st.markdown(
                "<div class='stat-number'>~40%</div>"
                "<div class='stat-caption'>of dementia cases could be prevented or slowed "
                "by modifying lifestyle factors</div>",
                unsafe_allow_html=True,
            )

st.markdown("<div class='bg-section'>About BrainGuard AI</div>", unsafe_allow_html=True)

vcol1, vcol2 = st.columns(2, gap="large")
with vcol1:
    with st.container(border=True, key="vision_card"):
        st.markdown("<span class='accent-bar accent-bar-blue'></span>", unsafe_allow_html=True)
        st.subheader("The Vision")
        st.write(
            "To democratize brain health data by turning a complex machine learning model "
            "into an interactive, public-facing dashboard. It serves two audiences: "
            "individuals looking to understand their modifiable risk factors, and "
            "clinicians who need an explainable, data-driven tool to back up their patient "
            "recommendations."
        )
with vcol2:
    with st.container(border=True, key="goal_card"):
        st.markdown("<span class='accent-bar accent-bar-violet'></span>", unsafe_allow_html=True)
        st.subheader("The Goal")
        st.write(
            "An end-to-end data science application that allows users to input "
            "health/lifestyle metrics, receive a personalized dementia risk assessment, "
            "and view an interactive, localized breakdown of why they received that score "
            "using Explainable AI (XAI)."
        )

st.subheader("The Core Question")
st.markdown(
    "<div class='pull-quote'>Can an explainable machine learning model accurately assess "
    "dementia risk using purely non-invasive, modifiable lifestyle factors, and how can we "
    "effectively visualize these risk drivers to motivate patient behavior change?</div>",
    unsafe_allow_html=True,
)

st.markdown("---")

st.subheader("Disclaimer")
st.warning(
    "BrainGuard AI is an **educational and clinical decision-support prototype**, "
    "not a diagnosis, a medical device, or a substitute for professional evaluation.\n\n"
    "A **Low Risk** result does not rule out dementia, and a **High Risk** result does "
    "not mean a person has or will develop dementia. The factors the model highlights "
    "are statistical associations, not proven causes.\n\n"
    "Always consult a qualified physician about any concerns regarding memory, "
    "thinking, or daily functioning."
)

st.markdown("---")
st.subheader("Contact")
st.info("support@brainguardai.com\n\nProject developed as part of a data science / AI course")
