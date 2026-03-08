from __future__ import annotations

from typing import Any, Protocol

from app.core.config import settings
from app.live.localization import normalize_locale


class LiveSpeechProvider(Protocol):
    def transcribe_audio_chunk(
        self,
        *,
        audio_base64: str,
        locale: str | None = None,
        transcript_hint: str | None = None,
    ) -> str | None:
        ...

    def synthesize_text(
        self,
        *,
        text: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        ...


class BrowserNativeLiveSpeechProvider:
    def transcribe_audio_chunk(
        self,
        *,
        audio_base64: str,
        locale: str | None = None,
        transcript_hint: str | None = None,
    ) -> str | None:
        _ = normalize_locale(locale)
        if not settings.LIVE_ENABLE_BROWSER_TRANSCRIPT_HINTS:
            return None
        if transcript_hint is None:
            return None
        text = transcript_hint.strip()
        return text or None

    def synthesize_text(
        self,
        *,
        text: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_locale(locale)
        return {
            "text": text,
            "audio_base64": None,
            "provider": "browser-native",
            "locale": normalized,
            "playback_mode": "browser_tts" if settings.LIVE_ENABLE_BROWSER_TTS else "text_only",
        }


class DefaultLiveSpeechProvider:
    def transcribe_audio_chunk(
        self,
        *,
        audio_base64: str,
        locale: str | None = None,
        transcript_hint: str | None = None,
    ) -> str | None:
        _ = audio_base64
        _ = transcript_hint
        _ = normalize_locale(locale)
        return None

    def synthesize_text(
        self,
        *,
        text: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_locale(locale)
        return {
            "text": text,
            "audio_base64": None,
            "provider": "fallback",
            "locale": normalized,
            "playback_mode": "text_only",
        }
