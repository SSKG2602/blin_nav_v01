"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { VoiceServerMessage } from "@/lib/types";

const WS_URL = "ws://localhost:8100/session";

type ConnectionState = "connecting" | "open" | "closed" | "error";

type UseLuminarSocketReturn = {
  connectionState: ConnectionState;
  sendUserTranscript: (payload: { sessionId: string; transcript: string }) => void;
  lastMessage: VoiceServerMessage | null;
};

export function useLuminarSocket(): UseLuminarSocketReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");
  const [lastMessage, setLastMessage] = useState<VoiceServerMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(WS_URL);
    wsRef.current = socket;

    socket.onopen = () => {
      setConnectionState("open");
    };

    socket.onclose = () => {
      setConnectionState("closed");
    };

    socket.onerror = () => {
      setConnectionState("error");
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as VoiceServerMessage;
        setLastMessage(parsed);
      } catch {
        setLastMessage({
          type: "agent_response",
          agentResponse: String(event.data)
        });
      }
    };

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, []);

  const sendUserTranscript = useCallback((payload: { sessionId: string; transcript: string }) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(
      JSON.stringify({
        type: "user_transcript",
        sessionId: payload.sessionId,
        transcript: payload.transcript,
        timestamp: new Date().toISOString()
      })
    );
  }, []);

  return {
    connectionState,
    sendUserTranscript,
    lastMessage
  };
}
