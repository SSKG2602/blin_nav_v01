"use client";

import { useVoiceSession } from "@/context/VoiceSessionContext";

export function VoiceTranscript() {
  const { transcript, interimTranscript, listening, speechError } = useVoiceSession();
  const content = interimTranscript || transcript || "Your words will appear here.";

  return (
    <section className="rounded-2xl border border-border bg-slate-50 p-4" aria-live="polite">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600">Transcript</h2>
        <span className={`text-xs font-medium ${listening ? "text-emerald-700" : "text-slate-500"}`}>
          {listening ? "Listening..." : "Idle"}
        </span>
      </div>
      <p className="mt-3 min-h-14 text-sm leading-6 text-slate-800">{content}</p>
      {speechError ? <p className="mt-2 text-xs text-red-600">{speechError}</p> : null}
    </section>
  );
}
