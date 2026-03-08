"use client";

export interface BrowserSpeechRecognitionAlternative {
  transcript: string;
}

export interface BrowserSpeechRecognitionResultLike {
  0: BrowserSpeechRecognitionAlternative;
  isFinal?: boolean;
  length: number;
}

export interface BrowserSpeechRecognitionEventLike extends Event {
  results: ArrayLike<BrowserSpeechRecognitionResultLike>;
}

export interface BrowserSpeechRecognitionInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives?: number;
  onresult: ((event: BrowserSpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

export interface BrowserSpeechRecognitionConstructor {
  new (): BrowserSpeechRecognitionInstance;
}

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  }
}

export function getSpeechRecognitionConstructor(): BrowserSpeechRecognitionConstructor | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}
