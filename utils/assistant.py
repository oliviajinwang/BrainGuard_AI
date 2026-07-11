import streamlit as st

MODEL = "claude-sonnet-5"

# Common questions get an instant, hardcoded answer instead of an LLM call --
# guaranteed safe (no risk of an ungrounded medical claim slipping through)
# and works even with no API key configured. Matched by substring against
# the lowercased user message; first match wins, so keep phrases specific.
FAQ_RULES = [
    (
        ["is this a diagnosis", "diagnose me", "do i have dementia", "does she have dementia",
         "does he have dementia", "am i going to get dementia"],
        "No — BrainGuard AI is a screening tool, not a diagnosis. It estimates modifiable "
        "risk factors based on the information you enter, but it can't examine anyone or "
        "confirm a real diagnosis. If you're worried about yourself or a family member, "
        "please talk to a primary care physician, who can arrange a proper cognitive "
        "evaluation.",
    ),
    (
        ["what does high risk mean", "what is high risk", "high risk result", "high risk mean"],
        "A \"High Risk\" result means the screening flagged a higher likelihood of "
        "modifiable dementia risk factors based on your answers. It is **not** a diagnosis "
        "— many people who score High Risk never go on to develop dementia. It's a signal "
        "worth discussing with a physician, not a cause for alarm on its own.",
    ),
    (
        ["what does low risk mean", "what is low risk", "low risk result"],
        "A \"Low Risk\" result means the screening didn't flag elevated risk based on the "
        "factors you entered. It isn't a guarantee, though — regular checkups are still the "
        "best way to catch changes early, especially as things like age change over time.",
    ),
    (
        ["how do i use this", "how does this work", "how do i check my risk", "how do i start"],
        "Go to **Quick Risk Check** in the sidebar, answer a few questions about age, "
        "education, and lifestyle factors (smoking, blood pressure, cholesterol, diabetes), "
        "and click **Check My Risk**. You'll get an estimated risk percentage and a "
        "plain-language breakdown of what influenced it.",
    ),
    (
        ["what factors", "risk factors", "modifiable", "what increases risk", "what causes dementia"],
        "This tool looks at *modifiable* risk factors — things that can potentially be "
        "changed or managed: smoking, hypertension (high blood pressure), high cholesterol, "
        "diabetes, and education level, alongside age and gender. Managing these is "
        "generally good for brain health, though it doesn't guarantee any individual outcome.",
    ),
    (
        ["what is dementia", "define dementia"],
        "Dementia is a general term for a decline in memory, thinking, or reasoning skills "
        "severe enough to interfere with daily life. It has several possible causes, and "
        "risk generally increases with age. If you want details specific to a person's "
        "situation, that's a conversation for their doctor.",
    ),
    (
        ["is my data private", "privacy", "is this confidential", "who sees my data"],
        "Quick Risk Check results aren't saved unless clinic staff register you as a "
        "patient. Your My AI Assistant chat is stored on your patient record by Patient ID "
        "after every message, so your clinic can review it under Patient AI Conversation — "
        "other patients never see your history.",
    ),
    (
        ["who made this", "about this app", "what is brainguard"],
        "BrainGuard AI is an explainable AI dementia risk screening tool — click **About** "
        "on the welcome screen for more on the project. It's a decision-support prototype, "
        "not a certified medical device.",
    ),
]

# Keeps the assistant strictly scoped: it explains the app and general,
# well-established dementia/brain-health facts, and firmly redirects
# anything that sounds like a personal medical question to a physician
# instead of answering it -- non-negotiable for a health-adjacent tool
# talking to worried family members, not clinicians.
SYSTEM_PROMPT = """You are the BrainGuard AI Assistant, embedded in a dementia risk \
screening tool used by family members and patients (not clinicians).

Your job:
- Explain what BrainGuard AI does and how to use it (Quick Risk Check, Register Patient)
- Explain general, well-established facts about dementia risk factors and brain health, \
in plain, warm, reassuring language
- Explain what terms or results in the app mean

Hard rules, never break these:
- You are NOT a doctor and NEVER diagnose, assess symptoms, or give personalized medical \
advice. If asked something that sounds like a personal medical question ("does my mother \
have dementia", "should I be worried about my memory"), acknowledge the concern warmly and \
firmly redirect to: talk to a primary care physician, who can arrange a proper cognitive \
evaluation.
- Never contradict or override what the app's own risk-check results say.
- If asked about anything outside dementia, brain health, or using this app, politely \
decline and redirect back to what you can help with.
- Keep answers short (2-4 sentences) and in plain, non-clinical language.
- Never claim certainty about someone's dementia risk or diagnosis status.
"""


def match_faq(user_message: str) -> str | None:
    lowered = user_message.lower()
    for keywords, answer in FAQ_RULES:
        if any(keyword in lowered for keyword in keywords):
            return answer
    return None


@st.cache_resource
def _load_client():
    # st.secrets raises StreamlitSecretNotFoundError (not KeyError) when no
    # secrets.toml exists at all, which is the normal state for local dev
    # without a key configured -- .get() alone doesn't catch that, so this
    # needs a broad try/except to degrade to FAQ-only mode instead of
    # crashing the page.
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        api_key = None
    if not api_key:
        return None
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def assistant_available() -> bool:
    """Whether the Claude API fallback is configured. FAQ matching always
    works regardless -- this only gates the open-ended fallback."""
    try:
        return _load_client() is not None
    except Exception:
        return False


def get_assistant_response(user_message: str, history: list[dict]) -> str:
    faq_answer = match_faq(user_message)
    if faq_answer is not None:
        return faq_answer

    client = _load_client()
    if client is None:
        return (
            "I can answer common questions about BrainGuard AI and general dementia risk "
            "factors, but I don't have an answer for that specific question right now. "
            "For anything about a real person's health, please talk to a physician."
        )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in history
                if m["role"] in ("user", "assistant")
            ]
            + [{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception:
        return (
            "Something went wrong reaching the assistant just now. In the meantime, for any "
            "question about a real person's health or symptoms, please talk to a physician."
        )
