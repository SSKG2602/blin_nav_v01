from __future__ import annotations

SUPPORTED_LOCALES = {"en-IN", "hi-IN"}

_MESSAGES: dict[str, dict[str, str]] = {
    "session_connected": {
        "en-IN": "Live session connected.",
        "hi-IN": "लाइव सेशन कनेक्ट हो गया है।",
    },
    "session_started": {
        "en-IN": "Wake path active. Listening for commands.",
        "hi-IN": "वेेक पाथ सक्रिय है। कमांड सुनने के लिए तैयार।",
    },
    "interrupted": {
        "en-IN": "Interruption acknowledged.",
        "hi-IN": "इंटरप्शन स्वीकार किया गया।",
    },
    "checkpoint_required": {
        "en-IN": "Checkpoint approval is required before continuing.",
        "hi-IN": "आगे बढ़ने से पहले चेकपॉइंट अनुमोदन आवश्यक है।",
    },
    "checkpoint_approved": {
        "en-IN": "Checkpoint approved. Resuming the guided flow.",
        "hi-IN": "चेकपॉइंट अनुमोदित हो गया। निर्देशित प्रवाह फिर से शुरू हो रहा है।",
    },
    "checkpoint_rejected": {
        "en-IN": "Checkpoint rejected. The session will stay safe and paused.",
        "hi-IN": "चेकपॉइंट अस्वीकृत हो गया। सेशन सुरक्षित रूप से रुका रहेगा।",
    },
    "final_confirmation_required": {
        "en-IN": "Final purchase confirmation is required before the terminal step.",
        "hi-IN": "अंतिम चरण से पहले अंतिम खरीद पुष्टि आवश्यक है।",
    },
    "final_confirmation_approved": {
        "en-IN": "Final purchase confirmation approved.",
        "hi-IN": "अंतिम खरीद पुष्टि स्वीकृत हो गई।",
    },
    "final_confirmation_rejected": {
        "en-IN": "Final purchase confirmation rejected.",
        "hi-IN": "अंतिम खरीद पुष्टि अस्वीकृत हो गई।",
    },
    "listening_started": {
        "en-IN": "Listening for your voice command.",
        "hi-IN": "आपके वॉइस कमांड के लिए सुन रहा हूँ।",
    },
    "listening_stopped": {
        "en-IN": "Voice listening stopped.",
        "hi-IN": "वॉइस सुनना बंद हो गया।",
    },
    "cancelled": {
        "en-IN": "Session cancellation received.",
        "hi-IN": "सेशन कैंसिलेशन प्राप्त हुआ।",
    },
    "error_generic": {
        "en-IN": "An error occurred in live session processing.",
        "hi-IN": "लाइव सेशन प्रोसेसिंग में त्रुटि हुई।",
    },
    "spoken_prefix": {
        "en-IN": "",
        "hi-IN": "सारांश: ",
    },
}


def normalize_locale(locale: str | None) -> str:
    if locale in SUPPORTED_LOCALES:
        return locale
    return "en-IN"


def localize_message(key: str, locale: str | None) -> str:
    normalized = normalize_locale(locale)
    localized = _MESSAGES.get(key, {})
    return localized.get(normalized) or localized.get("en-IN") or key


def localize_spoken_text(text: str, locale: str | None) -> str:
    normalized = normalize_locale(locale)
    prefix = localize_message("spoken_prefix", normalized)
    if not prefix:
        return text
    return f"{prefix}{text}"


def localize_prompt_text(text: str | None, locale: str | None, *, fallback_key: str | None = None) -> str | None:
    if not text and fallback_key is None:
        return None

    normalized = normalize_locale(locale)
    if normalized == "en-IN":
        if text:
            return text
        if fallback_key is not None:
            return localize_message(fallback_key, normalized)
        return None

    known_prompts = {
        "An OTP verification step is detected. Please confirm before continuing.": "ओटीपी सत्यापन चरण मिला है। आगे बढ़ने से पहले कृपया पुष्टि करें।",
        "A CAPTCHA challenge is detected. Please assist with manual verification.": "कैप्चा चुनौती मिली है। कृपया मैन्युअल सत्यापन में सहायता करें।",
        "Payment confirmation is required. Please confirm if I should continue.": "भुगतान पुष्टि आवश्यक है। कृपया बताएं कि मुझे जारी रखना चाहिए या नहीं।",
        "Address confirmation is required. Please verify the selected address.": "पते की पुष्टि आवश्यक है। कृपया चुने गए पते की पुष्टि करें।",
        "Final purchase confirmation is required. Please approve before proceeding.": "अंतिम खरीद पुष्टि आवश्यक है। आगे बढ़ने से पहले कृपया स्वीकृति दें।",
        "Checkout is ready. Please confirm final purchase.": "चेकआउट तैयार है। कृपया अंतिम खरीद की पुष्टि करें।",
        "Final purchase confirmation required before continuing.": "आगे बढ़ने से पहले अंतिम खरीद पुष्टि आवश्यक है।",
    }
    if text in known_prompts:
        return known_prompts[text]

    if fallback_key is not None:
        localized = localize_message(fallback_key, normalized)
        if localized:
            return localized
    return text
