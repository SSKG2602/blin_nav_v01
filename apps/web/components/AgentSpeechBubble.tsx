"use client";

import { useVoiceSession } from "@/context/VoiceSessionContext";

export function AgentSpeechBubble() {
  const { agentResponse, agentSpeaking } = useVoiceSession();

  return (
    <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4" aria-live="polite">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-800">Luminar</h2>
        <span className={`text-xs font-medium ${agentSpeaking ? "text-emerald-700" : "text-emerald-900/80"}`}>
          {agentSpeaking ? "Speaking..." : "Ready"}
        </span>
      </div>
      <p className="mt-3 min-h-14 text-sm leading-6 text-emerald-950">
        {agentResponse || "Ask me for a product, price limit, or category and I will start shopping."}
      </p>
    </section>
  );
}
