"use client";

type CartStatusIndicatorProps = {
  itemCount: number;
  subtotal?: string | null;
  currency?: string | null;
  updatedAt?: string | null;
};

function formatUpdatedAt(value?: string | null): string {
  if (!value) {
    return "just now";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleTimeString();
}

export function CartStatusIndicator({
  itemCount,
  subtotal,
  currency,
  updatedAt
}: CartStatusIndicatorProps) {
  return (
    <section className="rounded-2xl border border-border bg-white p-5 shadow-sm" aria-live="polite">
      <h2 className="text-base font-semibold text-slate-900">Cart</h2>
      <div className="mt-4 flex items-end justify-between gap-3">
        <p className="text-3xl font-semibold text-slate-900">{itemCount}</p>
        <p className="text-sm text-slate-500">items</p>
      </div>
      <p className="mt-3 text-sm text-slate-700">
        Subtotal: {subtotal || "Unknown"} {currency || ""}
      </p>
      <p className="mt-2 text-xs text-slate-500">Updated {formatUpdatedAt(updatedAt)}</p>
    </section>
  );
}
