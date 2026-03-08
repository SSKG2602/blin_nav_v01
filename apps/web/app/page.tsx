"use client";

import { AgentSpeechBubble } from "@/components/AgentSpeechBubble";
import { CartStatusIndicator } from "@/components/CartStatusIndicator";
import { NavigationStatusPanel } from "@/components/NavigationStatusPanel";
import { VoiceMicButton } from "@/components/VoiceMicButton";
import { VoiceTranscript } from "@/components/VoiceTranscript";
import { VoiceSessionProvider, useVoiceSession } from "@/context/VoiceSessionContext";

function LuminarVoiceScreen() {
  const { listening, startListening, stopListening, speechSupported } = useVoiceSession();

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(16,118,96,0.2),transparent_40%),linear-gradient(180deg,#f5fffc_0%,#e5f4ef_100%)] px-4 py-8 text-foreground sm:px-8">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-3xl border border-border bg-white/80 p-6 shadow-[0_20px_60px_rgba(7,32,27,0.1)] backdrop-blur-sm sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Luminar Voice Session
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
            Voice-first AI shopping assistant
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-700 sm:text-base">
            Press the microphone, speak your shopping goal, and Luminar will guide navigation in
            real time.
          </p>

          <div className="mt-8 flex flex-col items-center gap-4">
            <VoiceMicButton
              listening={listening}
              disabled={!speechSupported}
              onPress={listening ? stopListening : startListening}
            />
            <p className="text-xs text-slate-600" aria-live="polite">
              Keyboard: <kbd className="rounded bg-slate-100 px-1.5 py-0.5">Space</kbd> toggle mic,
              <kbd className="ml-1 rounded bg-slate-100 px-1.5 py-0.5">Esc</kbd> stop listening
            </p>
            {!speechSupported ? (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                Speech recognition is not available in this browser.
              </p>
            ) : null}
          </div>

          <div className="mt-8 grid gap-4">
            <VoiceTranscript />
            <AgentSpeechBubble />
          </div>
        </section>

        <aside className="grid gap-4 self-start">
          <NavigationStatusPanel />
          <CartStatusIndicator />
        </aside>
      </div>
    </main>
  );
}

export default function HomePage() {
  return (
    <VoiceSessionProvider>
      <LuminarVoiceScreen />
    </VoiceSessionProvider>
  );
}
