"use client";

type AgentSpeechBubbleProps = {
  agentResponse?: string | null;
  agentSpeaking?: boolean;
  title?: string;
  speakingLabel?: string;
  idleLabel?: string;
  placeholder?: string;
};

export function AgentSpeechBubble({
  agentResponse,
  agentSpeaking = false,
  title = "Luminar",
  speakingLabel = "Speaking...",
  idleLabel = "Ready",
  placeholder = "Ask me for a product, price limit, or category and I will start shopping."
}: AgentSpeechBubbleProps) {
  const content = agentResponse?.trim() || placeholder;

  return (
    <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4" aria-live="polite">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-800">{title}</h2>
        <span className={`text-xs font-medium ${agentSpeaking ? "text-emerald-700" : "text-emerald-900/80"}`}>
          {agentSpeaking ? speakingLabel : idleLabel}
        </span>
      </div>
      <p className="mt-3 min-h-14 text-sm leading-6 text-emerald-950">{content}</p>
    </section>
  );
}
