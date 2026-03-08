"use client";

type VoiceTranscriptProps = {
  transcript?: string | null;
  interimTranscript?: string | null;
  listening?: boolean;
  speechError?: string | null;
  placeholder?: string;
};

export function VoiceTranscript({
  transcript,
  interimTranscript,
  listening = false,
  speechError,
  placeholder = "Your words will appear here."
}: VoiceTranscriptProps) {
  const interim = interimTranscript?.trim() ?? "";
  const stable = transcript?.trim() ?? "";
  const content = interim || stable || placeholder;

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
