"use client";

import { useEffect, useRef, useState } from "react";
import {
  cancelLatestOrder,
  buildLiveWebSocketUrl,
  createLiveSession,
  getCurrentUser,
  getAmazonConnectionStatus,
  loadLatestOrderSnapshot,
  login,
  persistAuthToken,
  getRuntimeObservation,
  getRuntimeScreenshot,
  getSessionContext,
  listSessions,
  removeCartItem,
  resolveCheckpoint,
  resolveFinalConfirmation,
  signup,
  updateCartQuantity
} from "@/services/api";
import type {
  AgentStepResponse,
  AmazonConnectionStatus,
  ClarificationRequest,
  LiveGatewayEvent,
  OrderCancellationResult,
  RuntimeObservation,
  RuntimeScreenshot,
  SessionContextSnapshot,
  SessionSummary,
  SensitiveCheckpoint,
  TranscriptItem,
  UserProfile
} from "@/lib/types";
import {
  getSpeechRecognitionConstructor,
  type BrowserSpeechRecognitionEventLike,
  type BrowserSpeechRecognitionInstance
} from "@/lib/browser-speech";

const SUPPORTED_LOCALES = ["en-IN", "hi-IN"];
const VOICE_RECOGNITION_UNAVAILABLE_MESSAGE = "Voice recognition requires Chrome or Edge browser";
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";
const AUTH_STORAGE_KEY = "blindnav_auth_token";

function safeLocale(input: string): string {
  if (SUPPORTED_LOCALES.includes(input)) {
    return input;
  }
  return "en-IN";
}

function nowIso(): string {
  return new Date().toISOString();
}

function makeTranscript(role: TranscriptItem["role"], text: string): TranscriptItem {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    timestamp: nowIso()
  };
}

async function blobToBase64(blob: Blob): Promise<string> {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read audio blob."));
    reader.onloadend = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const encoded = result.includes(",") ? result.split(",")[1] ?? "" : result;
      resolve(encoded);
    };
    reader.readAsDataURL(blob);
  });
}

function stripSpokenPrefix(text: string, locale: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "";
  }

  const prefixes = locale === "hi-IN" ? ["सारांश: ", "Summary: "] : ["Summary: ", "सारांश: "];
  for (const prefix of prefixes) {
    if (trimmed.startsWith(prefix)) {
      return trimmed.slice(prefix.length).trim();
    }
  }
  return trimmed;
}

function stopMediaStream(stream: MediaStream | null) {
  if (!stream) {
    return;
  }
  stream.getTracks().forEach((track) => track.stop());
}

export function useDemoShell() {
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);
  const screenshotPollRef = useRef<number | null>(null);
  const wakeRecognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null);
  const wakePhraseEnabledRef = useRef(false);
  const wakeActiveRef = useRef(false);
  const recognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null);
  const pendingVoiceCaptureRef = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const transcriptHintRef = useRef<string | null>(null);
  const listeningTimeoutRef = useRef<number | null>(null);
  const playbackAudioRef = useRef<HTMLAudioElement | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [wakeActive, setWakeActive] = useState(false);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [locale, setLocale] = useState("en-IN");
  const [currentState, setCurrentState] = useState("SESSION_INITIALIZING");
  const [inputText, setInputText] = useState("");
  const [context, setContext] = useState<SessionContextSnapshot | null>(null);
  const [checkpoint, setCheckpoint] = useState<SensitiveCheckpoint | null>(null);
  const [clarification, setClarification] = useState<ClarificationRequest | null>(null);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [eventLog, setEventLog] = useState<string[]>([]);
  const [sessionHistory, setSessionHistory] = useState<SessionSummary[]>([]);
  const [runtimeObservation, setRuntimeObservation] = useState<RuntimeObservation | null>(null);
  const [runtimeScreenshot, setRuntimeScreenshot] = useState<RuntimeScreenshot | null>(null);
  const [browserActivityStatus, setBrowserActivityStatus] = useState("Waiting for a live browser session.");
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authDisplayName, setAuthDisplayName] = useState("");
  const [wakePhraseEnabled, setWakePhraseEnabled] = useState(false);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [audioCaptureSupported, setAudioCaptureSupported] = useState(false);
  const [voiceSupportMessage, setVoiceSupportMessage] = useState<string | null>(null);
  const [amazonConnected, setAmazonConnected] = useState(false);
  const [amazonCookiePanelOpen, setAmazonCookiePanelOpen] = useState(false);
  const [amazonCookieInput, setAmazonCookieInput] = useState("");
  const [amazonAuthBusy, setAmazonAuthBusy] = useState(false);
  const [amazonAuthNote, setAmazonAuthNote] = useState<string | null>(null);
  const [orderCancelBusy, setOrderCancelBusy] = useState(false);

  useEffect(() => {
    wakePhraseEnabledRef.current = wakePhraseEnabled;
  }, [wakePhraseEnabled]);

  useEffect(() => {
    wakeActiveRef.current = wakeActive;
  }, [wakeActive]);

  const appendTranscript = (item: TranscriptItem) => {
    setTranscript((prev) => [item, ...prev].slice(0, 120));
  };

  const appendEvent = (name: string) => {
    setEventLog((prev) => [`${nowIso()}  ${name}`, ...prev].slice(0, 120));
  };

  const refreshSessionHistory = async () => {
    try {
      const sessions = await listSessions(25);
      setSessionHistory(sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session history.");
    }
  };

  const refreshRuntimeObservationState = async (id: string, silent = false) => {
    try {
      const observation = await getRuntimeObservation(id);
      setRuntimeObservation(observation);
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : "Failed to refresh runtime observation.");
      }
    }
  };

  const refreshRuntimeScreenshotState = async (id: string, silent = false) => {
    try {
      const screenshot = await getRuntimeScreenshot(id);
      setRuntimeScreenshot(screenshot);
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : "Failed to refresh runtime screenshot.");
      }
    }
  };

  const refreshRuntimeState = async (id: string) => {
    try {
      const [observation, screenshot] = await Promise.all([
        getRuntimeObservation(id),
        getRuntimeScreenshot(id)
      ]);
      setRuntimeObservation(observation);
      setRuntimeScreenshot(screenshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh runtime state.");
    }
  };

  const refreshAmazonConnectionStatus = async (id: string, silent = false): Promise<AmazonConnectionStatus | null> => {
    try {
      const status = await getAmazonConnectionStatus(id);
      setAmazonConnected(status.connected);
      if (status.connected) {
        setAmazonAuthNote("Amazon Connected ✓");
      } else if (status.notes) {
        setAmazonAuthNote(status.notes);
      }
      return status;
    } catch (err) {
      if (!silent) {
        setError(err instanceof Error ? err.message : "Failed to inspect Amazon connection status.");
      }
      return null;
    }
  };

  const refreshContext = async (id: string) => {
    try {
      const ctx = await getSessionContext(id);
      setContext(ctx);
      setClarification(ctx.latest_clarification_request ?? null);
      if (ctx.latest_sensitive_checkpoint) {
        setCheckpoint(ctx.latest_sensitive_checkpoint);
      } else {
        setCheckpoint(null);
      }
      await refreshRuntimeObservationState(id, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh session context.");
    }
  };

  const stopPolling = () => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const stopScreenshotPolling = () => {
    if (screenshotPollRef.current !== null) {
      window.clearInterval(screenshotPollRef.current);
      screenshotPollRef.current = null;
    }
  };

  const startPolling = (id: string) => {
    stopPolling();
    pollRef.current = window.setInterval(() => {
      void refreshContext(id);
    }, 3000);
  };

  const startScreenshotPolling = (id: string) => {
    stopScreenshotPolling();
    void refreshRuntimeScreenshotState(id, true);
    screenshotPollRef.current = window.setInterval(() => {
      void refreshRuntimeScreenshotState(id, true);
    }, 2000);
  };

  const stopSpeechPlayback = () => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    if (playbackAudioRef.current) {
      playbackAudioRef.current.pause();
      playbackAudioRef.current = null;
    }
    setSpeaking(false);
  };

  const stopListening = () => {
    pendingVoiceCaptureRef.current = false;
    if (listeningTimeoutRef.current !== null) {
      window.clearTimeout(listeningTimeoutRef.current);
      listeningTimeoutRef.current = null;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    } else {
      stopMediaStream(mediaStreamRef.current);
      mediaStreamRef.current = null;
    }

    setListening(false);
  };

  const stopWakePhraseListener = () => {
    wakePhraseEnabledRef.current = false;
    setWakePhraseEnabled(false);
    if (wakeRecognitionRef.current) {
      wakeRecognitionRef.current.stop();
      wakeRecognitionRef.current = null;
    }
  };

  const ensureMicrophonePermission = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("Microphone access is not available in this browser.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stopMediaStream(stream);
  };

  const sendRecognizedUserText = (text: string) => {
    const ws = wsRef.current;
    const normalized = text.trim();
    if (!normalized || !ws || ws.readyState !== WebSocket.OPEN) {
      return false;
    }

    ws.send(
      JSON.stringify({
        type: "user_text",
        text: normalized,
        locale: safeLocale(locale)
      })
    );
    appendTranscript(makeTranscript("user", normalized));
    setBrowserActivityStatus(`Sent voice command: ${normalized}`);
    return true;
  };

  const startWakePhraseListener = () => {
    const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
    if (!SpeechRecognitionCtor) {
      setSpeechSupported(false);
      setVoiceSupportMessage(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      setError(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      return false;
    }

    stopWakePhraseListener();

    const recognition = new SpeechRecognitionCtor();
    wakeRecognitionRef.current = recognition;
    wakePhraseEnabledRef.current = true;
    setWakePhraseEnabled(true);
    recognition.lang = safeLocale(locale);
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event: BrowserSpeechRecognitionEventLike) => {
      const indexedEvent = event as BrowserSpeechRecognitionEventLike & { resultIndex?: number };
      const startIndex = typeof indexedEvent.resultIndex === "number" ? indexedEvent.resultIndex : 0;
      for (let index = startIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (!result?.isFinal) {
          continue;
        }
        const transcriptText = result[0]?.transcript?.trim().toLowerCase() ?? "";
        if (!transcriptText || !transcriptText.includes("luminar")) {
          continue;
        }

        wakeActiveRef.current = true;
        setWakeActive(true);
        appendTranscript(makeTranscript("system", 'Wake phrase "Luminar" detected. Listening for commands.'));
        setBrowserActivityStatus('Wake phrase detected. Listening for voice commands.');
        stopWakePhraseListener();
        if (connected && wsRef.current?.readyState === WebSocket.OPEN) {
          void startListening();
        } else {
          pendingVoiceCaptureRef.current = true;
        }
        return;
      }
    };
    recognition.onerror = () => {
      setError("Wake phrase listening failed. Please try again.");
      setBrowserActivityStatus("Wake phrase listening failed.");
      stopWakePhraseListener();
    };
    recognition.onend = () => {
      if (wakeRecognitionRef.current === recognition) {
        wakeRecognitionRef.current = null;
      }
      setWakePhraseEnabled(false);
      if (!wakeActiveRef.current && wakePhraseEnabledRef.current) {
        wakeRecognitionRef.current = recognition;
        recognition.start();
        wakePhraseEnabledRef.current = true;
        setWakePhraseEnabled(true);
      }
    };
    recognition.start();
    return true;
  };

  const closeConnection = () => {
    stopListening();
    stopWakePhraseListener();
    stopSpeechPlayback();
    stopScreenshotPolling();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
    wakeActiveRef.current = false;
    setWakeActive(false);
    wakePhraseEnabledRef.current = false;
    setWakePhraseEnabled(false);
    setAmazonConnected(false);
    setAmazonCookiePanelOpen(false);
    setAmazonCookieInput("");
    setAmazonAuthBusy(false);
    setAmazonAuthNote(null);
    setBrowserActivityStatus("Waiting for a live browser session.");
    stopPolling();
  };

  useEffect(() => {
    const supported = Boolean(getSpeechRecognitionConstructor());
    setSpeechSupported(supported);
    setAudioCaptureSupported(
      typeof window !== "undefined" &&
        typeof navigator !== "undefined" &&
        Boolean(navigator.mediaDevices?.getUserMedia) &&
        typeof MediaRecorder !== "undefined"
    );
    setVoiceSupportMessage(supported ? null : VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
    void (async () => {
      try {
        const auth = await getCurrentUser();
        setCurrentUser(auth.profile);
        if (auth.profile.preferred_locale) {
          setLocale(safeLocale(auth.profile.preferred_locale));
        }
      } catch {
        persistAuthToken(null);
      }
    })();
    void refreshSessionHistory();
    return () => {
      closeConnection();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const playSpokenPayload = async (data: Record<string, unknown>) => {
    stopSpeechPlayback();

    const audioBase64 = typeof data.audio_base64 === "string" ? data.audio_base64 : null;
    const text = typeof data.text === "string" ? data.text : "";
    const payloadLocale = typeof data.locale === "string" ? data.locale : safeLocale(locale);
    const playbackMode = typeof data.playback_mode === "string" ? data.playback_mode : null;
    const cleanText = stripSpokenPrefix(text, payloadLocale);

    if (audioBase64) {
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      playbackAudioRef.current = audio;
      setSpeaking(true);
      audio.onended = () => {
        setSpeaking(false);
        playbackAudioRef.current = null;
      };
      try {
        await audio.play();
        return;
      } catch {
        setSpeaking(false);
      }
    }

    if (
      cleanText &&
      typeof window !== "undefined" &&
      "speechSynthesis" in window &&
      (playbackMode === "browser_tts" || playbackMode === null)
    ) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = safeLocale(payloadLocale);
      utterance.rate = 0.9;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      setBrowserActivityStatus("Speaking...");
      requestAnimationFrame(() => {
        window.speechSynthesis.speak(utterance);
      });
    }
  };

  const handleIncomingEvent = (payload: LiveGatewayEvent) => {
    appendEvent(payload.event);

    if (payload.event === "session_connected") {
      if (typeof payload.data.locale === "string") {
        setLocale(safeLocale(payload.data.locale));
      }
      const message =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : "Live session connected.";
      appendTranscript(makeTranscript("system", message));
      setBrowserActivityStatus("Browser session connected. Waiting for the live start event.");
      return;
    }

    if (payload.event === "session_started") {
      const message =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : "Wake path active. Listening for commands.";
      appendTranscript(makeTranscript("system", message));
      setBrowserActivityStatus("Live session started. Waiting for the user's shopping request.");
      return;
    }

    if (payload.event === "transcription") {
      const text = typeof payload.data.text === "string" ? payload.data.text : "";
      if (text) {
        appendTranscript(makeTranscript("user", text));
        setBrowserActivityStatus("Captured user speech and sent it to the agent.");
      }
      return;
    }

    if (payload.event === "interpreted_intent") {
      const action = typeof payload.data.action === "string" ? payload.data.action : "UNKNOWN";
      appendTranscript(makeTranscript("system", `Interpreted intent: ${action}`));
      setBrowserActivityStatus(`Preparing browser actions for ${action.toLowerCase().replaceAll("_", " ")}.`);
      return;
    }

    if (payload.event === "agent_step") {
      const response = payload.data as unknown as AgentStepResponse;
      if (typeof response.new_state === "string") {
        setCurrentState(response.new_state);
      }
      setBrowserActivityStatus(
        response.spoken_summary?.trim() || `Browser state changed to ${response.new_state}.`
      );
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "spoken_output") {
      const text = typeof payload.data.text === "string" ? payload.data.text : "";
      const payloadLocale = typeof payload.data.locale === "string" ? payload.data.locale : safeLocale(locale);
      const cleanedText = stripSpokenPrefix(text, payloadLocale);
      if (text) {
        appendTranscript(makeTranscript("assistant", cleanedText || text));
      }
      void playSpokenPayload(payload.data);
      return;
    }

    if (payload.event === "checkpoint_required") {
      const incoming = payload.data as unknown as SensitiveCheckpoint;
      setCheckpoint(incoming);
      const localizedMessage =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : null;
      appendTranscript(
        makeTranscript("warning", localizedMessage || incoming.prompt_to_user || "Checkpoint required.")
      );
      setBrowserActivityStatus("Browser flow paused for a sensitive checkpoint.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "clarification_required") {
      const incoming = payload.data as unknown as ClarificationRequest;
      setClarification(incoming);
      const localizedMessage =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : null;
      appendTranscript(
        makeTranscript(
          "warning",
          localizedMessage || incoming.prompt_to_user || "Clarification is required before continuing."
        )
      );
      setBrowserActivityStatus("Waiting for clarification before the browser continues.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "clarification_resolved") {
      setClarification((prev) =>
        prev
          ? {
              ...prev,
              status: typeof payload.data.approved === "boolean" && !payload.data.approved ? "REJECTED" : "APPROVED"
            }
          : prev
      );
      appendTranscript(
        makeTranscript(
          "system",
          typeof payload.data.message === "string" && payload.data.message
            ? payload.data.message
            : "Clarification response sent."
        )
      );
      setBrowserActivityStatus("Clarification response sent. Resuming browser flow.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "checkpoint_resolved") {
      const incoming = payload.data as unknown as SensitiveCheckpoint;
      setCheckpoint(incoming);
      appendTranscript(makeTranscript("system", `Checkpoint resolved: ${incoming.status}`));
      setBrowserActivityStatus("Checkpoint resolved. Browser flow can continue.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "final_confirmation_required") {
      const message =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : "Final confirmation is required.";
      appendTranscript(makeTranscript("warning", message));
      setBrowserActivityStatus("Waiting for final purchase confirmation.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "final_confirmation_resolved") {
      appendTranscript(
        makeTranscript(
          "system",
          typeof payload.data.message === "string" && payload.data.message
            ? payload.data.message
            : "Final confirmation resolved."
        )
      );
      setBrowserActivityStatus("Final confirmation resolved.");
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "interrupted") {
      const message =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : "Interruption acknowledged.";
      appendTranscript(makeTranscript("warning", message));
      stopSpeechPlayback();
      setBrowserActivityStatus("User interruption received. Re-anchoring the browser flow.");
      return;
    }

    if (payload.event === "error") {
      const detail = typeof payload.data.detail === "string" ? payload.data.detail : "Unknown error";
      setError(detail);
      appendTranscript(makeTranscript("warning", detail));
      setBrowserActivityStatus(`Browser activity error: ${detail}`);
      return;
    }
  };

  const startLiveSession = async () => {
    if (connecting || connected) {
      return;
    }

    setError(null);
    setConnecting(true);
    setWakeActive(false);

    try {
      const live = await createLiveSession({
        merchant: "amazon.in",
        locale: safeLocale(locale)
      });

      setSessionId(live.session_id);
      if (live.locale) {
        setLocale(safeLocale(live.locale));
      }
      await refreshContext(live.session_id);
      await refreshRuntimeScreenshotState(live.session_id, true);
      await refreshAmazonConnectionStatus(live.session_id, true);
      await refreshSessionHistory();
      startPolling(live.session_id);
      startScreenshotPolling(live.session_id);
      setBrowserActivityStatus("Starting a live browser session on amazon.in.");

      const ws = new WebSocket(buildLiveWebSocketUrl(live.websocket_path));
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setConnecting(false);
        ws.send(
          JSON.stringify({
            type: "start",
            locale: safeLocale(locale)
          })
        );
        if (pendingVoiceCaptureRef.current) {
          void startListening();
        }
      };

      ws.onclose = () => {
        setConnected(false);
        setConnecting(false);
        setWakeActive(false);
        setWakePhraseEnabled(false);
        setListening(false);
        stopPolling();
        stopScreenshotPolling();
        stopSpeechPlayback();
      };

      ws.onerror = () => {
        setError("WebSocket connection error.");
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as LiveGatewayEvent;
          handleIncomingEvent(payload);
        } catch {
          setError("Failed to parse incoming live event.");
        }
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start live session.");
      setConnecting(false);
      setWakeActive(false);
    }
  };

  const handleAuthSuccess = (profile: UserProfile, token: string) => {
    persistAuthToken(token);
    setCurrentUser(profile);
    if (profile.preferred_locale) {
      setLocale(safeLocale(profile.preferred_locale));
    }
  };

  const loginUser = async () => {
    if (!authEmail.trim() || !authPassword.trim()) {
      setError("Email and password are required.");
      return;
    }
    setAuthBusy(true);
    setError(null);
    try {
      const response = await login({
        email: authEmail.trim(),
        password: authPassword
      });
      handleAuthSuccess(response.profile, response.token);
      setAuthPassword("");
      appendTranscript(makeTranscript("system", `Signed in as ${response.profile.display_name}.`));
      await refreshSessionHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setAuthBusy(false);
    }
  };

  const signupUser = async () => {
    if (!authEmail.trim() || !authPassword.trim() || !authDisplayName.trim()) {
      setError("Display name, email, and password are required.");
      return;
    }
    setAuthBusy(true);
    setError(null);
    try {
      const response = await signup({
        email: authEmail.trim(),
        displayName: authDisplayName.trim(),
        password: authPassword,
        preferredLocale: safeLocale(locale)
      });
      handleAuthSuccess(response.profile, response.token);
      setAuthPassword("");
      appendTranscript(makeTranscript("system", `Account created for ${response.profile.display_name}.`));
      await refreshSessionHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setAuthBusy(false);
    }
  };

  const logoutUser = () => {
    persistAuthToken(null);
    closeConnection();
    setCurrentUser(null);
    setSessionHistory([]);
    appendTranscript(makeTranscript("system", "Signed out of demo profile."));
    void refreshSessionHistory();
  };

  const sendUserText = () => {
    const ws = wsRef.current;
    const text = inputText.trim();
    if (!ws || ws.readyState !== WebSocket.OPEN || !text) {
      return;
    }
    ws.send(
      JSON.stringify({
        type: "user_text",
        text,
        locale: safeLocale(locale)
      })
    );
    appendTranscript(makeTranscript("user", text));
    setInputText("");
  };

  const startListening = async () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || listening) {
      return;
    }

    const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
    if (!SpeechRecognitionCtor) {
      setSpeechSupported(false);
      setVoiceSupportMessage(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      setError(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      return;
    }

    setError(null);
    setVoiceSupportMessage(null);
    transcriptHintRef.current = null;
    audioChunksRef.current = [];

    try {
      await ensureMicrophonePermission();

      const recognition = new SpeechRecognitionCtor();
      recognitionRef.current = recognition;
      recognition.lang = safeLocale(locale);
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event: BrowserSpeechRecognitionEventLike) => {
        const indexedEvent = event as BrowserSpeechRecognitionEventLike & { resultIndex?: number };
        const startIndex = typeof indexedEvent.resultIndex === "number" ? indexedEvent.resultIndex : 0;
        for (let index = startIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          if (!result?.isFinal) {
            continue;
          }
          const transcriptText = result[0]?.transcript?.trim() ?? "";
          if (transcriptText) {
            transcriptHintRef.current = transcriptText;
            sendRecognizedUserText(transcriptText);
          }
        }
      };
      recognition.onerror = () => {
        setError("Speech recognition failed. You can still type commands.");
        setBrowserActivityStatus("Speech recognition failed. Type the command instead.");
        stopListening();
      };
      recognition.onend = () => {
        setListening(false);
        recognitionRef.current = null;
      };
      recognition.start();

      setListening(true);
      pendingVoiceCaptureRef.current = false;
      appendTranscript(makeTranscript("system", "Listening for your voice command."));
      setBrowserActivityStatus("Listening for voice commands.");
    } catch (err) {
      stopListening();
      setError(err instanceof Error ? err.message : "Microphone access failed.");
    }
  };

  const startWakeSequence = async () => {
    if (connecting || wakePhraseEnabled || wakeActive) {
      return;
    }

    const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
    if (!SpeechRecognitionCtor) {
      setSpeechSupported(false);
      setVoiceSupportMessage(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      setError(VOICE_RECOGNITION_UNAVAILABLE_MESSAGE);
      return;
    }

    setSpeechSupported(true);
    setError(null);
    setVoiceSupportMessage(null);
    wakeActiveRef.current = false;
    setWakeActive(false);
    pendingVoiceCaptureRef.current = false;

    try {
      await ensureMicrophonePermission();
      setBrowserActivityStatus('Listening for the wake phrase "Luminar"...');
      appendTranscript(makeTranscript("system", 'Microphone ready. Say "Luminar" to begin speaking.'));

      if (!connected) {
        await startLiveSession();
        if (!wsRef.current) {
          return;
        }
      }

      startWakePhraseListener();
    } catch (err) {
      setWakePhraseEnabled(false);
      setWakeActive(false);
      setError(err instanceof Error ? err.message : "Microphone access failed.");
    }
  };

  const sendInterrupt = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    stopListening();
    stopSpeechPlayback();
    ws.send(JSON.stringify({ type: "interrupt", locale: safeLocale(locale) }));
  };

  const sendCancel = () => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    stopListening();
    stopSpeechPlayback();
    ws.send(JSON.stringify({ type: "cancel", locale: safeLocale(locale) }));
  };

  const resolveActiveCheckpoint = async (approved: boolean) => {
    if (!sessionId) {
      return;
    }
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "checkpoint_response",
          approved,
          resolution_notes: approved ? "approved in demo shell" : "rejected in demo shell",
          locale: safeLocale(locale)
        })
      );
      return;
    }

    try {
      const resolved = await resolveCheckpoint({
        sessionId,
        approved,
        resolutionNotes: approved ? "Approved in demo shell." : "Rejected in demo shell."
      });
      setCheckpoint(resolved);
      appendTranscript(makeTranscript("system", `Checkpoint ${resolved.status.toLowerCase()}.`));
      await refreshContext(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve checkpoint.");
    }
  };

  const resolveFinalPurchase = async (approved: boolean) => {
    if (!sessionId) {
      return;
    }
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "final_confirmation_response",
          approved,
          resolution_notes: approved ? "approved in demo shell" : "rejected in demo shell",
          locale: safeLocale(locale)
        })
      );
      return;
    }

    try {
      await resolveFinalConfirmation({
        sessionId,
        approved,
        resolutionNotes: approved ? "Approved in demo shell." : "Rejected in demo shell."
      });
      appendTranscript(
        makeTranscript(
          "system",
          approved ? "Final purchase confirmation approved." : "Final purchase confirmation rejected."
        )
      );
      await refreshContext(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve final confirmation.");
    }
  };

  const respondToClarification = (approved: boolean) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(
      JSON.stringify({
        type: "user_text",
        text: approved ? "yes" : "no",
        locale: safeLocale(locale)
      })
    );
    appendTranscript(
      makeTranscript("user", approved ? "yes" : "no")
    );
  };

  const removeCartLine = async (itemId?: string | null, title?: string | null) => {
    if (!sessionId) {
      return;
    }
    try {
      await removeCartItem({
        sessionId,
        itemId,
        title
      });
      appendTranscript(
        makeTranscript("system", `Requested cart removal for ${title ?? itemId ?? "selected item"}.`)
      );
      await refreshContext(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove cart item.");
    }
  };

  const updateCartLineQuantity = async (
    quantity: number,
    itemId?: string | null,
    title?: string | null
  ) => {
    if (!sessionId) {
      return;
    }
    try {
      await updateCartQuantity({
        sessionId,
        itemId,
        title,
        quantity
      });
      appendTranscript(
        makeTranscript(
          "system",
          `Updated quantity for ${title ?? itemId ?? "selected item"} to ${quantity}.`
        )
      );
      await refreshContext(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update cart quantity.");
    }
  };

  const fetchLatestOrderSnapshot = async () => {
    if (!sessionId) {
      return;
    }
    try {
      setBrowserActivityStatus("Loading the latest order details from amazon.in.");
      await loadLatestOrderSnapshot(sessionId);
      appendTranscript(makeTranscript("system", "Loaded latest order details from the merchant site."));
      await refreshContext(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load latest order snapshot.");
    }
  };

  const cancelPlacedOrder = async () => {
    if (!sessionId) {
      return;
    }
    setOrderCancelBusy(true);
    setError(null);
    setBrowserActivityStatus("Attempting to cancel the latest order from amazon.in.");
    try {
      const result: OrderCancellationResult = await cancelLatestOrder(sessionId);
      appendTranscript(makeTranscript(result.cancelled ? "assistant" : "warning", result.spoken_summary));
      setBrowserActivityStatus(result.spoken_summary);
      await refreshContext(sessionId);
      await refreshRuntimeScreenshotState(sessionId, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel the latest order.");
    } finally {
      setOrderCancelBusy(false);
    }
  };

  const connectAmazonIn = async () => {
    if (!sessionId) {
      setError("Start a live session before connecting Amazon.in.");
      return;
    }
    setError(null);
    setAmazonCookiePanelOpen(true);
    setAmazonAuthNote(
      "Paste the exported Amazon.in cookies JSON for the active BlindNav session."
    );
    setBrowserActivityStatus("Waiting for pasted Amazon.in cookies.");
  };

  const saveAmazonCookies = async () => {
    if (!sessionId) {
      setError("Start a live session before saving Amazon.in cookies.");
      return;
    }

    const cookies = amazonCookieInput.trim();
    if (!cookies) {
      const message = "Paste exported Amazon.in cookies JSON before saving.";
      setAmazonAuthNote(message);
      setError(message);
      return;
    }

    setAmazonAuthBusy(true);
    setError(null);
    setAmazonAuthNote("Saving Amazon.in cookies into the BlindNav runtime...");
    setBrowserActivityStatus("Loading pasted Amazon.in cookies into the live browser session.");

    try {
      const authToken =
        typeof window === "undefined" ? null : window.localStorage.getItem(AUTH_STORAGE_KEY);
      const response = await fetch(`${API_BASE_URL}/api/auth/amazon/cookies`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify({
          session_id: sessionId,
          cookies
        }),
        cache: "no-store"
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Amazon cookie save failed.");
      }

      const payload = (await response.json()) as { connected?: boolean };
      if (payload.connected !== true) {
        throw new Error("Amazon cookie save did not confirm a connected runtime session.");
      }

      setAmazonConnected(true);
      setAmazonAuthNote("Amazon Connected ✓");
      setAmazonCookieInput("");
      setAmazonCookiePanelOpen(false);
      appendTranscript(makeTranscript("system", "Amazon Connected ✓"));
      setBrowserActivityStatus("Amazon.in cookies loaded into the runtime session.");
      await refreshAmazonConnectionStatus(sessionId, true);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save Amazon.in cookies.";
      setAmazonConnected(false);
      setAmazonAuthNote(message);
      setError(message);
      setBrowserActivityStatus("Amazon.in cookie load failed.");
    } finally {
      setAmazonAuthBusy(false);
    }
  };

  return {
    sessionId,
    currentUser,
    authBusy,
    authMode,
    setAuthMode,
    authEmail,
    setAuthEmail,
    authPassword,
    setAuthPassword,
    authDisplayName,
    setAuthDisplayName,
    wakePhraseEnabled,
    setWakePhraseEnabled,
    wakeActive,
    connected,
    connecting,
    locale,
    setLocale,
    currentState,
    inputText,
    setInputText,
    context,
    checkpoint,
    clarification,
    transcript,
    eventLog,
    sessionHistory,
    runtimeObservation,
    runtimeScreenshot,
    browserActivityStatus,
    error,
    listening,
    speaking,
    speechSupported,
    audioCaptureSupported,
    voiceSupportMessage,
    amazonConnected,
    amazonCookiePanelOpen,
    amazonCookieInput,
    setAmazonCookieInput,
    amazonAuthBusy,
    amazonAuthNote,
    orderCancelBusy,
    finalConfirmationPending:
      context?.latest_final_purchase_confirmation?.required === true &&
      context?.latest_final_purchase_confirmation?.confirmed !== true,
    clarificationPending: clarification?.status === "PENDING",
    finalConfirmation: context?.latest_final_purchase_confirmation ?? null,
    loginUser,
    signupUser,
    logoutUser,
    startWakeSequence,
    startLiveSession,
    startListening,
    stopListening,
    sendUserText,
    sendInterrupt,
    sendCancel,
    respondToClarification,
    removeCartLine,
    updateCartLineQuantity,
    fetchLatestOrderSnapshot,
    cancelPlacedOrder,
    connectAmazonIn,
    saveAmazonCookies,
    resolveActiveCheckpoint,
    resolveFinalPurchase,
    closeConnection,
    refreshSessionHistory,
    refreshRuntimeState: sessionId ? () => refreshRuntimeState(sessionId) : async () => undefined
  };
}
