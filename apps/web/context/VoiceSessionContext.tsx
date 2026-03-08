"use client";

import {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import { useLuminarSocket } from "@/hooks/useLuminarSocket";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { CartState, NavigationState } from "@/lib/types";

type VoiceSessionContextValue = {
  listening: boolean;
  transcript: string;
  agentResponse: string;
  sessionId: string;
  navigationState: NavigationState;
  cartState: CartState;
  interimTranscript: string;
  connectionState: "connecting" | "open" | "closed" | "error";
  speechSupported: boolean;
  speechError: string | null;
  agentSpeaking: boolean;
  startListening: () => void;
  stopListening: () => void;
};

const VoiceSessionContext = createContext<VoiceSessionContextValue | null>(null);

function newSessionId() {
  return `luminar-${crypto.randomUUID()}`;
}

function speakText(text: string, onStart: () => void, onEnd: () => void) {
  if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) {
    return;
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.onstart = onStart;
  utterance.onend = onEnd;
  utterance.onerror = onEnd;

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

export function VoiceSessionProvider({ children }: PropsWithChildren) {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [transcript, setTranscript] = useState("");
  const [agentResponse, setAgentResponse] = useState("");
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [navigationState, setNavigationState] = useState<NavigationState>({
    status: "Idle",
    step: "Waiting for your first request",
    updatedAt: new Date().toISOString()
  });
  const [cartState, setCartState] = useState<CartState>({
    itemCount: 0
  });

  const { connectionState, sendUserTranscript, lastMessage } = useLuminarSocket();

  const handleUserSpeechStart = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setAgentSpeaking(false);
    }
  }, []);

  const handleFinalTranscript = useCallback(
    (spokenText: string) => {
      setTranscript(spokenText);
      sendUserTranscript({ sessionId, transcript: spokenText });
    },
    [sendUserTranscript, sessionId]
  );

  const {
    listening,
    interimTranscript,
    speechSupported,
    error: speechError,
    startListening,
    stopListening
  } = useSpeechRecognition({
    onFinalTranscript: handleFinalTranscript,
    onSpeechStart: handleUserSpeechStart
  });

  useEffect(() => {
    if (!lastMessage) {
      return;
    }

    if (lastMessage.sessionId) {
      setSessionId(lastMessage.sessionId);
    }

    if (lastMessage.transcript) {
      setTranscript(lastMessage.transcript);
    }

    if (lastMessage.agentResponse) {
      setAgentResponse(lastMessage.agentResponse);
      speakText(lastMessage.agentResponse, () => setAgentSpeaking(true), () => setAgentSpeaking(false));
    }

    if (lastMessage.navigationState) {
      setNavigationState((previous) => ({
        ...previous,
        ...lastMessage.navigationState,
        updatedAt: new Date().toISOString()
      }));
    }

    if (lastMessage.cart) {
      setCartState((previous) => ({
        ...previous,
        ...lastMessage.cart,
        updatedAt: new Date().toISOString()
      }));
    }
  }, [lastMessage]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTypingContext =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.getAttribute("contenteditable") === "true";

      if (isTypingContext) {
        return;
      }

      if (event.code === "Space") {
        event.preventDefault();
        if (listening) {
          stopListening();
        } else {
          startListening();
        }
      }

      if (event.code === "Escape" && listening) {
        stopListening();
      }
    };

    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [listening, startListening, stopListening]);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const value = useMemo<VoiceSessionContextValue>(
    () => ({
      listening,
      transcript,
      agentResponse,
      sessionId,
      navigationState,
      cartState,
      interimTranscript,
      connectionState,
      speechSupported,
      speechError,
      agentSpeaking,
      startListening,
      stopListening
    }),
    [
      listening,
      transcript,
      agentResponse,
      sessionId,
      navigationState,
      cartState,
      interimTranscript,
      connectionState,
      speechSupported,
      speechError,
      agentSpeaking,
      startListening,
      stopListening
    ]
  );

  return <VoiceSessionContext.Provider value={value}>{children}</VoiceSessionContext.Provider>;
}

export function useVoiceSession() {
  const context = useContext(VoiceSessionContext);

  if (!context) {
    throw new Error("useVoiceSession must be used inside VoiceSessionProvider.");
  }

  return context;
}
