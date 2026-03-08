from __future__ import annotations

from app.core.config import settings
from app.live.speech import (
    BrowserNativeLiveSpeechProvider,
    DefaultLiveSpeechProvider,
    LiveSpeechProvider,
)

if settings.LIVE_SPEECH_PROVIDER == "browser-native":
    _speech_provider_singleton: LiveSpeechProvider = BrowserNativeLiveSpeechProvider()
else:
    _speech_provider_singleton = DefaultLiveSpeechProvider()


def get_live_speech_provider() -> LiveSpeechProvider:
    return _speech_provider_singleton
