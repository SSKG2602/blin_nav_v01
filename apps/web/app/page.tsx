const stack = [
  "Next.js 15",
  "TypeScript",
  "Tailwind CSS",
  "shadcn/ui scaffold",
  "FastAPI",
  "PostgreSQL",
  "Redis",
  "Playwright Python",
  "Cloud Run"
];

const ports = [
  { label: "Frontend", value: "3100" },
  { label: "Backend API", value: "8100" },
  { label: "Docs / Devtools", value: "4100" }
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(214,180,80,0.16),transparent_35%),linear-gradient(180deg,#fcfaf4_0%,#f4efe2_100%)] px-6 py-12 text-foreground">
      <div className="mx-auto flex max-w-5xl flex-col gap-8">
        <section className="rounded-3xl border border-border bg-white/80 p-8 shadow-[0_20px_80px_rgba(61,46,22,0.08)] backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-amber-700">
            UI Navigator Track
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">
            BlindNav / Luminar foundation initialized
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-700">
            This frontend is a scaffold-only shell for the BlindNav hackathon repository. No
            shopping flows, merchant logic, voice loop, or browser automation are implemented in
            this page.
          </p>
        </section>

        <section className="grid gap-6 md:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-border bg-white/75 p-6">
            <h2 className="text-lg font-semibold">Pinned stack notes</h2>
            <ul className="mt-4 grid gap-3 text-sm text-slate-700 md:grid-cols-2">
              {stack.map((item) => (
                <li key={item} className="rounded-2xl border border-border bg-slate-50 px-4 py-3">
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-3xl border border-border bg-slate-950 p-6 text-slate-50">
            <h2 className="text-lg font-semibold">Pinned ports</h2>
            <ul className="mt-4 space-y-3 text-sm">
              {ports.map((port) => (
                <li key={port.label} className="flex items-center justify-between rounded-2xl bg-white/10 px-4 py-3">
                  <span>{port.label}</span>
                  <span className="font-mono text-amber-300">{port.value}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-slate-300">
              Primary demo merchant is <span className="font-medium text-white">amazon.in</span>.
              Flipkart and Meesho remain backup logged-in contingencies only.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
