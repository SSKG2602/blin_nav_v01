"use client";

import { useEffect, useRef, useState } from "react";
import {
  buildLiveWebSocketUrl,
  createLiveSession,
  getCheckpoint,
  getRuntimeObservation,
  getRuntimeScreenshot,
  getSessionContext,
  listSessions,
  resolveCheckpoint,
  resolveFinalConfirmation
} from "@/services/api";
import type {
  AgentStepResponse,
  LiveGatewayEvent,
  RuntimeObservation,
  RuntimeScreenshot,
  SessionContextSnapshot,
  SessionSummary,
  SensitiveCheckpoint,
  TranscriptItem
} from "@/lib/types";
import {
  getSpeechRecognitionConstructor,
  type BrowserSpeechRecognitionEventLike,
  type BrowserSpeechRecognitionInstance
} from "@/lib/browser-speech";

const SUPPORTED_LOCALES = ["en-IN", "hi-IN"];

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

function stopMediaStream(stream: MediaStream | null) {
  if (!stream) {
    return;
  }
  stream.getTracks().forEach((track) => track.stop());
}

export function useDemoShell() {
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<number | null>(null);
  const recognitionRef = useRef<BrowserSpeechRecognitionInstance | null>(null);
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
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [eventLog, setEventLog] = useState<string[]>([]);
  const [sessionHistory, setSessionHistory] = useState<SessionSummary[]>([]);
  const [runtimeObservation, setRuntimeObservation] = useState<RuntimeObservation | null>(null);
  const [runtimeScreenshot, setRuntimeScreenshot] = useState<RuntimeScreenshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [audioCaptureSupported, setAudioCaptureSupported] = useState(false);

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

  const refreshContext = async (id: string) => {
    try {
      const ctx = await getSessionContext(id);
      setContext(ctx);
      if (ctx.latest_sensitive_checkpoint) {
        setCheckpoint(ctx.latest_sensitive_checkpoint);
      } else {
        const checkpointResult = await getCheckpoint(id);
        setCheckpoint(checkpointResult);
      }
      await refreshRuntimeState(id);
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

  const startPolling = (id: string) => {
    stopPolling();
    pollRef.current = window.setInterval(() => {
      void refreshContext(id);
    }, 3000);
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

  const closeConnection = () => {
    stopListening();
    stopSpeechPlayback();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
    setConnecting(false);
    setWakeActive(false);
    stopPolling();
  };

  useEffect(() => {
    setSpeechSupported(Boolean(getSpeechRecognitionConstructor()));
    setAudioCaptureSupported(
      typeof window !== "undefined" &&
        typeof navigator !== "undefined" &&
        Boolean(navigator.mediaDevices?.getUserMedia) &&
        typeof MediaRecorder !== "undefined"
    );
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
      text &&
      typeof window !== "undefined" &&
      "speechSynthesis" in window &&
      (playbackMode === "browser_tts" || playbackMode === null)
    ) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = payloadLocale;
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);
      setSpeaking(true);
      window.speechSynthesis.speak(utterance);
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
      return;
    }

    if (payload.event === "session_started") {
      const message =
        typeof payload.data.message === "string" && payload.data.message
          ? payload.data.message
          : "Wake path active. Listening for commands.";
      appendTranscript(makeTranscript("system", message));
      return;
    }

    if (payload.event === "transcription") {
      const text = typeof payload.data.text === "string" ? payload.data.text : "";
      if (text) {
        appendTranscript(makeTranscript("user", text));
      }
      return;
    }

    if (payload.event === "interpreted_intent") {
      const action = typeof payload.data.action === "string" ? payload.data.action : "UNKNOWN";
      appendTranscript(makeTranscript("system", `Interpreted intent: ${action}`));
      return;
    }

    if (payload.event === "agent_step") {
      const response = payload.data as unknown as AgentStepResponse;
      if (typeof response.new_state === "string") {
        setCurrentState(response.new_state);
      }
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "spoken_output") {
      const text = typeof payload.data.text === "string" ? payload.data.text : "";
      if (text) {
        appendTranscript(makeTranscript("assistant", text));
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
      if (sessionId) {
        void refreshContext(sessionId);
      }
      return;
    }

    if (payload.event === "checkpoint_resolved") {
      const incoming = payload.data as unknown as SensitiveCheckpoint;
      setCheckpoint(incoming);
      appendTranscript(makeTranscript("system", `Checkpoint resolved: ${incoming.status}`));
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
      return;
    }

    if (payload.event === "error") {
      const detail = typeof payload.data.detail === "string" ? payload.data.detail : "Unknown error";
      setError(detail);
      appendTranscript(makeTranscript("warning", detail));
      return;
    }
  };

  const startLiveSession = async () => {
    if (connecting || connected) {
      return;
    }

    setError(null);
    setConnecting(true);
    setWakeActive(true);

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
      await refreshSessionHistory();
      startPolling(live.session_id);

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
      };

      ws.onclose = () => {
        setConnected(false);
        setConnecting(false);
        setWakeActive(false);
        setListening(false);
        stopPolling();
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

    setError(null);
    transcriptHintRef.current = null;
    audioChunksRef.current = [];

    const SpeechRecognitionCtor = getSpeechRecognitionConstructor();
    if (!SpeechRecognitionCtor && !audioCaptureSupported) {
      setError("Browser speech APIs are unavailable.");
      return;
    }

    try {
      if (audioCaptureSupported && navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        const recorder = new MediaRecorder(stream);
        mediaRecorderRef.current = recorder;
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
        recorder.onstop = async () => {
          const currentWs = wsRef.current;
          const transcriptHint = transcriptHintRef.current?.trim() || null;
          const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
          audioChunksRef.current = [];
          stopMediaStream(mediaStreamRef.current);
          mediaStreamRef.current = null;
          mediaRecorderRef.current = null;

          if (!currentWs || currentWs.readyState !== WebSocket.OPEN) {
            return;
          }

          if (blob.size > 0) {
            try {
              const audioBase64 = await blobToBase64(blob);
              currentWs.send(
                JSON.stringify({
                  type: "audio_chunk",
                  audio_base64: audioBase64,
                  transcript_hint: transcriptHint,
                  locale: safeLocale(locale)
                })
              );
              return;
            } catch {
              // fall through to transcript-only path
            }
          }

          if (transcriptHint) {
            currentWs.send(
              JSON.stringify({
                type: "user_text",
                text: transcriptHint,
                locale: safeLocale(locale)
              })
            );
          }
        };
        recorder.start();
      }

      if (SpeechRecognitionCtor) {
        const recognition = new SpeechRecognitionCtor();
        recognitionRef.current = recognition;
        recognition.lang = safeLocale(locale);
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.onresult = (event: BrowserSpeechRecognitionEventLike) => {
          const result = event.results?.[0]?.[0]?.transcript?.trim() ?? "";
          if (result) {
            transcriptHintRef.current = result;
          }
          if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.stop();
          } else if (ws.readyState === WebSocket.OPEN && result) {
            ws.send(
              JSON.stringify({
                type: "user_text",
                text: result,
                locale: safeLocale(locale)
              })
            );
          }
        };
        recognition.onerror = () => {
          setError("Speech recognition failed. You can still type commands.");
          stopListening();
        };
        recognition.onend = () => {
          if (mediaRecorderRef.current?.state === "recording") {
            mediaRecorderRef.current.stop();
          } else {
            setListening(false);
          }
          recognitionRef.current = null;
        };
        recognition.start();
      }

      setListening(true);
      appendTranscript(makeTranscript("system", "Listening for your voice command."));
      listeningTimeoutRef.current = window.setTimeout(() => {
        stopListening();
      }, 6500);
    } catch (err) {
      stopListening();
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

  return {
    sessionId,
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
    transcript,
    eventLog,
    sessionHistory,
    runtimeObservation,
    runtimeScreenshot,
    error,
    listening,
    speaking,
    speechSupported,
    audioCaptureSupported,
    finalConfirmationPending:
      context?.latest_final_purchase_confirmation?.required === true &&
      context?.latest_final_purchase_confirmation?.confirmed !== true,
    finalConfirmation: context?.latest_final_purchase_confirmation ?? null,
    startLiveSession,
    startListening,
    stopListening,
    sendUserText,
    sendInterrupt,
    sendCancel,
    resolveActiveCheckpoint,
    resolveFinalPurchase,
    closeConnection,
    refreshSessionHistory,
    refreshRuntimeState: sessionId ? () => refreshRuntimeState(sessionId) : async () => undefined
  };
}
