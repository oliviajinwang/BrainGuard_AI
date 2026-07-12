from __future__ import annotations

import os
import time
from typing import Any

import streamlit as st
from openai import OpenAI

# Cheap default model for short educational chatbot responses.
DEFAULT_MODEL = "gpt-5-nano"

# Cost controls.
MAX_HISTORY_MESSAGES = 8
MAX_USER_MESSAGE_CHARS = 2_000
MAX_OUTPUT_TOKENS = 200

# Rate limit -- bounds worst-case API spend per browser session (roughly
# per-patient, since each session signs in as one patient at a time). Only
# gates the paid OpenAI call, not the free local FAQ match below.
RATE_LIMIT_MAX_MESSAGES = 5
RATE_LIMIT_WINDOW_SECONDS = 60

FAQ_RULES: list[tuple[list[str], str]] = [
    (
        [
            "is this a diagnosis",
            "diagnose me",
            "do i have dementia",
            "does she have dementia",
            "does he have dementia",
            "am i going to get dementia",
        ],
        "No. BrainGuard AI is a screening and educational tool, not a diagnosis. "
        "It cannot examine anyone or determine whether a person has dementia. "
        "Please discuss personal symptoms or concerns with a licensed physician.",
    ),
    (
        ["what does high risk mean", "what is high risk", "high risk result"],
        'A "High Risk" result means the screening model found a pattern associated '
        "with higher risk in its training data. It is not a diagnosis, and it does "
        "not mean that the person will develop dementia. A physician can help "
        "interpret concerns in the context of a full evaluation.",
    ),
    (
        ["what does low risk mean", "what is low risk", "low risk result"],
        'A "Low Risk" result means the screening did not flag elevated risk from the '
        "entered factors. It is not a guarantee, and new or worsening symptoms should "
        "still be discussed with a physician.",
    ),
    (
        [
            "how do i use this",
            "how does this work",
            "how do i check my risk",
            "how do i start",
        ],
        "Open the Dementia Check page, choose an assessment, enter the requested "
        "information, and run the model. The app will display an experimental estimate "
        "and a plain-language explanation of the factors that influenced it.",
    ),
    (
        ["what factors", "risk factors", "modifiable", "what increases risk"],
        "The lifestyle assessment considers age, education, smoking, hypertension, "
        "high cholesterol, diabetes, and gender. Some factors may be manageable, but "
        "the app cannot recommend a personal treatment plan.",
    ),
    (
        ["what is dementia", "define dementia"],
        "Dementia is a general term for changes in memory, thinking, or reasoning that "
        "interfere with daily life. It can have several causes, so personal concerns "
        "should be evaluated by a qualified healthcare professional.",
    ),
    (
        ["what is alzheimer", "what is alzheimer's", "alzheimer disease"],
        "Alzheimer's disease is the most common cause of dementia. Dementia is a broad "
        "term for symptoms affecting memory and thinking, while Alzheimer's is one "
        "specific disease that can cause those symptoms.",
    ),
    (
        ["what is mmse", "mmse score", "what does mmse mean"],
        "The MMSE, or Mini-Mental State Examination, is a short cognitive screening "
        "test. It measures areas such as memory, attention, language, and orientation. "
        "It cannot diagnose dementia by itself.",
    ),
    (
        ["what is nwbv", "normalized whole brain volume"],
        "Normalized whole brain volume, or nWBV, estimates the proportion of the skull "
        "occupied by brain tissue. In research, lower values may be associated with "
        "brain tissue loss, but one measurement does not establish a diagnosis.",
    ),
    (
        ["what is etiv", "intracranial volume"],
        "Estimated intracranial volume, or eTIV, is an estimate of the total volume "
        "inside the skull. It is often used to help compare brain-volume measurements "
        "across people with different head sizes.",
    ),
    (
        ["what is asf", "atlas scaling factor"],
        "Atlas scaling factor, or ASF, describes how much a person's brain scan must be "
        "scaled to align with a standard brain atlas. It is a technical imaging measure, "
        "not a diagnosis.",
    ),
    (
        ["what is shap", "shap values", "feature importance"],
        "SHAP is an explainability method that estimates how each input affected a "
        "particular model prediction. Positive and negative contributions show how "
        "features changed the model output, but they do not prove cause and effect.",
    ),
    (
        ["how accurate", "model accuracy", "accuracy of brainguard"],
        "BrainGuard's performance depends on the specific model and dataset. Accuracy "
        "alone can be misleading, especially when one class is rare, so recall, "
        "precision, F1 score, and AUC should also be considered.",
    ),
    (
        ["what dataset", "training data", "oasis dataset"],
        "The structural model uses research data derived from the OASIS longitudinal "
        "dataset. Results may not generalize to every population, and the model has not "
        "been clinically validated.",
    ),
    (
        ["smoking", "cigarettes", "tobacco"],
        "Smoking is associated with vascular damage and may increase long-term risk for "
        "cognitive decline. Stopping smoking can benefit overall cardiovascular and brain "
        "health, but personal medical decisions should be discussed with a clinician.",
    ),
    (
        ["hypertension", "high blood pressure", "blood pressure"],
        "High blood pressure can damage blood vessels over time, including vessels that "
        "support the brain. Managing it is generally important for cardiovascular and "
        "brain health, but a clinician should advise on individual treatment.",
    ),
    (
        ["cholesterol", "high cholesterol"],
        "High cholesterol can contribute to blood-vessel disease, which may affect brain "
        "health over time. It is only one part of overall risk and should be interpreted "
        "with other medical information.",
    ),
    (
        ["diabetes", "blood sugar"],
        "Diabetes can affect blood vessels and is associated with higher risk of several "
        "health problems, including cognitive decline. Individual care should be guided "
        "by a licensed healthcare professional.",
    ),
    (
        ["education", "years of education"],
        "Education may appear in dementia-risk models because it can be associated with "
        "cognitive reserve and other social factors. It does not mean that less education "
        "directly causes dementia.",
    ),
    (
        ["is my data private", "privacy", "is this confidential", "who sees my data"],
        "Messages on this page are saved to the selected patient record and can be "
        "reviewed by clinic users of this prototype. Do not enter information you do "
        "not want stored in that record.",
    ),
    (
        ["who made this", "about this app", "what is brainguard"],
        "BrainGuard AI is an explainable machine-learning prototype for exploring "
        "patterns associated with dementia risk. It is not a certified medical device.",
    ),
]

SYSTEM_PROMPT = """
You are the BrainGuard AI Assistant inside an educational dementia-risk screening
prototype used by patients and family members.

You may:
- explain how BrainGuard AI works;
- explain the meaning and limitations of its screens and model outputs;
- provide brief, general, well-established educational information about dementia,
  brain health, and common risk factors.

Safety and scope rules:
- Never diagnose, estimate an individual's true medical risk, interpret symptoms,
  recommend medication changes, or provide a personal treatment plan.
- When a user asks about a real person's symptoms, acknowledge the concern briefly and
  direct them to a licensed physician or primary-care clinician for an evaluation.
- For sudden or severe symptoms, advise contacting local emergency services.
- Never claim that an app result confirms or rules out dementia.
- Do not contradict the application's displayed result.
- Do not ask for additional sensitive medical details.
- Stay within dementia education, brain health, and use of this application.
- Keep answers warm, clear, and concise, normally 2-5 sentences.
""".strip()


def _read_setting(name: str) -> str | None:
    """Read a Streamlit secret first, then an environment variable."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value).strip()
    except Exception:
        pass

    value = os.getenv(name)
    return value.strip() if value else None


@st.cache_resource
def _load_client() -> OpenAI | None:
    """Create and cache the OpenAI client."""
    api_key = _read_setting("OPENAI_API_KEY")
    if not api_key:
        return None

    return OpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=2,
    )


def assistant_available() -> bool:
    """Return True when an OpenAI API key is configured."""
    return _load_client() is not None


def _check_rate_limit() -> bool:
    """Sliding-window limiter over st.session_state. Returns False if the
    caller should be blocked from making another paid API call right now."""
    now = time.time()
    timestamps: list[float] = st.session_state.setdefault("_assistant_api_call_times", [])
    timestamps[:] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]

    if len(timestamps) >= RATE_LIMIT_MAX_MESSAGES:
        return False

    timestamps.append(now)
    return True


def match_faq(user_message: str) -> str | None:
    """Answer common questions locally so they cost nothing."""
    lowered = user_message.casefold()

    for keywords, answer in FAQ_RULES:
        if any(keyword in lowered for keyword in keywords):
            return answer

    return None


def _clean_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Validate and limit conversation history sent to OpenAI."""
    cleaned: list[dict[str, str]] = []

    for item in history:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = str(item.get("content") or "").strip()

        if role not in {"user", "assistant"} or not content:
            continue

        cleaned.append(
            {
                "role": role,
                "content": content[:MAX_USER_MESSAGE_CHARS],
            }
        )

    cleaned = cleaned[-MAX_HISTORY_MESSAGES:]

    if cleaned and cleaned[0]["role"] == "assistant":
        cleaned = cleaned[1:]

    return cleaned


def get_assistant_response(
    user_message: str,
    history: list[dict[str, Any]],
) -> str:
    """Return a local FAQ answer or an OpenAI-generated answer."""
    message = user_message.strip()

    if not message:
        return "Please enter a question."

    if len(message) > MAX_USER_MESSAGE_CHARS:
        return (
            f"Please shorten your message to fewer than "
            f"{MAX_USER_MESSAGE_CHARS:,} characters."
        )

    faq_answer = match_faq(message)
    if faq_answer is not None:
        return faq_answer

    if not _check_rate_limit():
        return (
            f"You're sending messages a bit quickly -- please wait a moment before "
            f"asking another question (limit: {RATE_LIMIT_MAX_MESSAGES} per "
            f"{RATE_LIMIT_WINDOW_SECONDS} seconds)."
        )

    client = _load_client()
    if client is None:
        return (
            "The extended assistant is not configured right now. I can still answer "
            "common questions about BrainGuard AI and general dementia risk factors. "
            "For concerns about a real person's health, please contact a physician."
        )

    model = _read_setting("OPENAI_MODEL") or DEFAULT_MODEL
    messages = _clean_history(history)
    messages.append({"role": "user", "content": message})

    try:
        response = client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=messages,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            reasoning={"effort": "minimal"},
        )

        reply = response.output_text.strip()

        if not reply:
            return (
                "The assistant returned an empty response. Please try rephrasing "
                "your question."
            )

        return reply

    except Exception as exc:
        print(f"BrainGuard assistant error: {type(exc).__name__}")

        return (
            "I couldn't reach the extended assistant just now. Common BrainGuard "
            "questions will still work. For personal health concerns, please contact "
            "a licensed physician."
        )