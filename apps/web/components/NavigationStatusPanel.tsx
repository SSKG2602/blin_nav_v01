"use client";

import { useVoiceSession } from "@/context/VoiceSessionContext";

export function NavigationStatusPanel() {
  const { sessionId, connectionState, navigationState } = useVoiceSession();

  return (
    <section className="rounded-2xl border border-border bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">Navigation Status</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex items-center justify-between gap-3">
          <dt className="text-slate-500">Socket</dt>
          <dd className="font-medium capitalize text-slate-900">{connectionState}</dd>
        </div>
        <div className="flex items-center justify-between gap-3">
          <dt className="text-slate-500">Status</dt>
          <dd className="font-medium text-slate-900">{navigationState.status}</dd>
        </div>
        <div className="space-y-1">
          <dt className="text-slate-500">Current Step</dt>
          <dd className="font-medium text-slate-900">{navigationState.step}</dd>
        </div>
        {navigationState.url ? (
          <div className="space-y-1">
            <dt className="text-slate-500">Target URL</dt>
            <dd className="break-all font-mono text-xs text-slate-800">{navigationState.url}</dd>
          </div>
        ) : null}
      </dl>
      <p className="mt-4 border-t border-border pt-3 font-mono text-xs text-slate-500">{sessionId}</p>
    </section>
  );
}
