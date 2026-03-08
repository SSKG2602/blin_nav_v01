"use client";

import { useVoiceSession } from "@/context/VoiceSessionContext";

export function CartStatusIndicator() {
  const { cartState } = useVoiceSession();

  return (
    <section className="rounded-2xl border border-border bg-white p-5 shadow-sm" aria-live="polite">
      <h2 className="text-base font-semibold text-slate-900">Cart</h2>
      <div className="mt-4 flex items-end justify-between gap-3">
        <p className="text-3xl font-semibold text-slate-900">{cartState.itemCount}</p>
        <p className="text-sm text-slate-500">items</p>
      </div>
      <p className="mt-3 text-sm text-slate-700">
        Subtotal: {cartState.subtotal || "Unknown"} {cartState.currency || ""}
      </p>
      <p className="mt-2 text-xs text-slate-500">
        Updated {cartState.updatedAt ? new Date(cartState.updatedAt).toLocaleTimeString() : "just now"}
      </p>
    </section>
  );
}
