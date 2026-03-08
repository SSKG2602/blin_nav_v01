"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getSpeechRecognitionFactory, SpeechRecognition } from "@/lib/speech";

type UseSpeechRecognitionParams = {
  onFinalTranscript: (text: string) => void;
  onSpeechStart?: () => void;
};

type UseSpeechRecognitionReturn = {
  listening: boolean;
  interimTranscript: string;
  speechSupported: boolean;
  error: string | null;
  startListening: () => void;
  stopListening: () => void;
};

export function useSpeechRecognition({
  onFinalTranscript,
  onSpeechStart
}: UseSpeechRecognitionParams): UseSpeechRecognitionReturn {
  const [listening, setListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const speechSupported = useMemo(() => getSpeechRecognitionFactory() !== null, []);

  useEffect(() => {
    const Factory = getSpeechRecognitionFactory();

    if (!Factory) {
      return;
    }

    const recognition = new Factory();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      setListening(true);
      setError(null);
      onSpeechStart?.();
    };

    recognition.onresult = (event) => {
      let interim = "";

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const text = event.results[index][0].transcript.trim();

        if (event.results[index].isFinal && text) {
          onFinalTranscript(text);
        } else {
          interim = `${interim} ${text}`.trim();
        }
      }

      setInterimTranscript(interim);
    };

    recognition.onerror = (event) => {
      setError(event.message || event.error || "Speech recognition failed");
    };

    recognition.onend = () => {
      setListening(false);
      setInterimTranscript("");
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
      recognitionRef.current = null;
    };
  }, [onFinalTranscript, onSpeechStart]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      return;
    }

    recognitionRef.current.start();
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  return {
    listening,
    interimTranscript,
    speechSupported,
    error,
    startListening,
    stopListening
  };
}
