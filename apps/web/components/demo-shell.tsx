"use client";

import { useMemo } from "react";
import { AgentSpeechBubble } from "@/components/AgentSpeechBubble";
import { NavigationStatusPanel } from "@/components/NavigationStatusPanel";
import { VoiceMicButton } from "@/components/VoiceMicButton";
import { VoiceTranscript } from "@/components/VoiceTranscript";
import { useDemoShell } from "@/hooks/use-demo-shell";

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function formatBooleanState(value: boolean | null | undefined): string {
  if (value === true) {
    return "yes";
  }
  if (value === false) {
    return "no";
  }
  return "unknown";
}

function formatSessionStatusLabel(value: string): string {
  if (!value) {
    return "unknown";
  }
  return `${value.slice(0, 1).toUpperCase()}${value.slice(1)}`;
}

export function DemoShell() {
  const demo = useDemoShell();

  const lowConfidenceActive = demo.context?.latest_low_confidence_status?.active === true;
  const recoveryActive = demo.context?.latest_recovery_status?.active === true;
  const checkpointPending = demo.checkpoint?.status === "PENDING";
  const finalConfirmation = demo.finalConfirmation;
  const finalConfirmationPending = demo.finalConfirmationPending;
  const postPurchase = demo.context?.latest_post_purchase_summary;
  const connectionState = demo.connected ? "connected" : demo.connecting ? "connecting" : "disconnected";
  const navigationStep =
    demo.context?.latest_multimodal_assessment?.recommended_next_step ??
    demo.context?.latest_multimodal_assessment?.decision ??
    "No recommended step yet";
  const micDisabled =
    !demo.connected || (!demo.listening && !demo.speechSupported && !demo.audioCaptureSupported);

  const statusTone = useMemo(() => {
    if (lowConfidenceActive) {
      return "border-rose-400 bg-rose-50 text-rose-900";
    }
    if (recoveryActive) {
      return "border-amber-400 bg-amber-50 text-amber-900";
    }
    return "border-emerald-400 bg-emerald-50 text-emerald-900";
  }, [lowConfidenceActive, recoveryActive]);
  const latestAssistantUtterance = useMemo(
    () => demo.transcript.find((item) => item.role === "assistant")?.text ?? null,
    [demo.transcript]
  );
  const latestUserUtterance = useMemo(
    () => demo.transcript.find((item) => item.role === "user")?.text ?? null,
    [demo.transcript]
  );

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(10,76,61,0.14),transparent_38%),linear-gradient(180deg,#f9fcfb_0%,#eef6f3_100%)] px-4 py-6 text-slate-900 md:px-8">
      <div className="mx-auto grid w-full max-w-7xl gap-5 xl:grid-cols-[1.45fr_1fr]">
        <section className="rounded-3xl border border-slate-300 bg-white p-5 shadow-sm xl:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                BlindNav / Luminar Demo Shell
              </p>
              <h1 className="mt-1 text-2xl font-semibold">Operator Console</h1>
            </div>
            <div className={`rounded-2xl border px-4 py-2 text-sm font-medium ${statusTone}`}>
              {demo.connected ? "Live Connected" : demo.connecting ? "Connecting" : "Disconnected"}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-slate-300 bg-slate-50 px-3 py-1 font-mono">
              Session: {demo.sessionId ?? "not started"}
            </span>
            {checkpointPending ? (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 font-medium text-amber-900">
                Checkpoint Pending
              </span>
            ) : null}
            {finalConfirmationPending ? (
              <span className="rounded-full border border-indigo-300 bg-indigo-50 px-3 py-1 font-medium text-indigo-900">
                Final Confirmation Pending
              </span>
            ) : null}
            {lowConfidenceActive ? (
              <span className="rounded-full border border-rose-300 bg-rose-50 px-3 py-1 font-medium text-rose-900">
                Low-Confidence Halt
              </span>
            ) : null}
            {recoveryActive ? (
              <span className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 font-medium text-amber-900">
                Recovery Active
              </span>
            ) : null}
          </div>
          {demo.error ? (
            <p className="mt-3 rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {demo.error}
            </p>
          ) : null}
        </section>

        <section className="space-y-5">
          <article className="rounded-3xl border border-slate-300 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Voice Controls</h2>
            <p className="mt-1 text-sm text-slate-600">
              Start session, capture voice input, and issue interrupt/cancel actions.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <label className="flex flex-col gap-1 text-sm">
                Locale
                <select
                  className="rounded-xl border border-slate-300 bg-white px-3 py-2"
                  value={demo.locale}
                  onChange={(event) => demo.setLocale(event.target.value)}
                >
                  <option value="en-IN">en-IN</option>
                  <option value="hi-IN">hi-IN</option>
                </select>
              </label>
              <button
                type="button"
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                onClick={demo.startLiveSession}
                disabled={demo.connecting || demo.connected}
              >
                {demo.wakeActive ? "Luminar Awake" : "Wake Luminar"}
              </button>
              <div className="flex items-center justify-center md:justify-start">
                <VoiceMicButton
                  listening={demo.listening}
                  disabled={micDisabled}
                  onPress={demo.listening ? demo.stopListening : demo.startListening}
                />
              </div>
              <button
                type="button"
                className="rounded-xl border border-slate-400 px-4 py-2 text-sm font-medium disabled:border-slate-200 disabled:text-slate-400"
                onClick={demo.sendInterrupt}
                disabled={!demo.connected}
              >
                Interrupt
              </button>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600">
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Speech recognition: {demo.speechSupported ? "available" : "unavailable"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Audio capture: {demo.audioCaptureSupported ? "available" : "unavailable"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Playback: {demo.speaking ? "speaking" : "idle"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Voice capture: {demo.listening ? "listening" : "idle"}
              </span>
              <button
                type="button"
                className="rounded-xl border border-rose-400 px-4 py-2 text-sm font-medium text-rose-700"
                onClick={demo.sendCancel}
                disabled={!demo.connected}
              >
                Cancel Session
              </button>
            </div>
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Transcript / Spoken Exchange</h2>
            <div className="mt-3 grid gap-3 xl:grid-cols-2">
              <VoiceTranscript
                transcript={latestUserUtterance}
                listening={demo.listening}
                placeholder="No recent user utterance yet."
              />
              <AgentSpeechBubble
                agentResponse={latestAssistantUtterance}
                agentSpeaking={demo.speaking}
                placeholder="No recent assistant spoken output yet."
              />
            </div>
            <div className="mt-3 flex gap-2">
              <input
                value={demo.inputText}
                onChange={(event) => demo.setInputText(event.target.value)}
                placeholder="Type user instruction..."
                className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="button"
                className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-medium text-white"
                onClick={demo.sendUserText}
                disabled={!demo.connected}
              >
                Send
              </button>
            </div>
            <div className="mt-4 max-h-[420px] space-y-2 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-3">
              {demo.transcript.length === 0 ? (
                <p className="text-sm text-slate-500">No transcript or spoken exchange yet.</p>
              ) : (
                demo.transcript.map((item) => (
                  <article
                    key={item.id}
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs uppercase tracking-wide text-slate-500">
                      <span>{item.role}</span>
                      <span>{formatDate(item.timestamp)}</span>
                    </div>
                    <p className="mt-1 text-slate-900">{item.text}</p>
                  </article>
                ))
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Checkpoint / Final Confirmation</h2>
            {checkpointPending ? (
                <div className="mt-3 space-y-3">
                  <p className="text-sm text-slate-700">{demo.checkpoint?.prompt_to_user}</p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded-xl bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
                      onClick={() => demo.resolveActiveCheckpoint(true)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="rounded-xl border border-rose-400 px-4 py-2 text-sm font-medium text-rose-700"
                      onClick={() => demo.resolveActiveCheckpoint(false)}
                    >
                      Reject
                    </button>
                  </div>
                </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No pending checkpoint.</p>
            )}
            <p className="mt-3 text-sm text-slate-600">
              Final confirmation required:{" "}
              <span className="font-medium">{formatBooleanState(finalConfirmation?.required)}</span>
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Final confirmation approved:{" "}
              <span className="font-medium">{formatBooleanState(finalConfirmation?.confirmed)}</span>
            </p>
            {finalConfirmationPending ? (
                <div className="mt-3 space-y-3 rounded-2xl border border-indigo-200 bg-indigo-50 p-3">
                  <p className="text-sm text-indigo-900">
                    {finalConfirmation?.prompt_to_user ?? "Explicit final purchase confirmation is required."}
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded-xl bg-indigo-700 px-4 py-2 text-sm font-medium text-white"
                      onClick={() => demo.resolveFinalPurchase(true)}
                    >
                      Confirm Purchase
                    </button>
                    <button
                      type="button"
                      className="rounded-xl border border-slate-400 px-4 py-2 text-sm font-medium"
                      onClick={() => demo.resolveFinalPurchase(false)}
                    >
                      Reject
                    </button>
                  </div>
                  {finalConfirmation?.confirmation_phrase_expected ? (
                    <p className="text-xs text-indigo-800">
                      Expected phrase: <span className="font-mono">{finalConfirmation.confirmation_phrase_expected}</span>
                    </p>
                  ) : null}
                </div>
            ) : null}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Event Stream</h2>
            <div className="mt-3 max-h-64 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs">
              {demo.eventLog.length === 0 ? (
                <p className="text-slate-500">No events yet.</p>
              ) : (
                demo.eventLog.map((item) => (
                  <p key={item} className="mb-1 text-slate-700">
                    {item}
                  </p>
                ))
              )}
            </div>
          </article>
        </section>

        <aside className="space-y-5">
          <article className="rounded-3xl border border-slate-300 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Safety Signals</h2>
            <div className="mt-3 space-y-2">
              {demo.error ? (
                <p className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  Current error: {demo.error}
                </p>
              ) : null}
              {lowConfidenceActive ? (
                <p className="rounded-xl border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  Low-confidence halt active.
                </p>
              ) : null}
              {recoveryActive ? (
                <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  Recovery active: {demo.context?.latest_recovery_status?.recovery_kind ?? "UNKNOWN"}
                </p>
              ) : null}
              {checkpointPending ? (
                <p className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  A sensitive checkpoint is waiting for user approval.
                </p>
              ) : null}
              {finalConfirmationPending ? (
                <p className="rounded-xl border border-indigo-300 bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
                  Final purchase confirmation is required before order placement.
                </p>
              ) : null}
              {!demo.error &&
              !lowConfidenceActive &&
              !recoveryActive &&
              !checkpointPending &&
              !finalConfirmationPending ? (
                <p className="rounded-xl border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                  No active risk or consent blockers.
                </p>
              ) : null}
            </div>
          </article>

          <NavigationStatusPanel
            sessionId={demo.sessionId}
            connectionState={connectionState}
            status={demo.currentState}
            step={navigationStep}
            url={demo.runtimeObservation?.observed_url}
          />

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Execution Assessment</h2>
            <p className="mt-2 text-sm text-slate-600">
              Decision:{" "}
              <span className="font-mono">
                {demo.context?.latest_multimodal_assessment?.decision ?? "n/a"}
              </span>
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Confidence:{" "}
              <span className="font-mono">
                {demo.context?.latest_multimodal_assessment?.confidence ?? "n/a"}
              </span>
            </p>
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Post-Purchase Summary</h2>
            {postPurchase ? (
              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>Item: {postPurchase.order_item_title ?? "n/a"}</p>
                <p>Price: {postPurchase.order_price_text ?? "n/a"}</p>
                <p>Delivery: {postPurchase.delivery_window_text ?? "n/a"}</p>
                <p className="rounded-xl bg-slate-100 px-3 py-2">
                  {postPurchase.spoken_summary || "No spoken summary available yet."}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No post-purchase evidence yet.</p>
            )}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Runtime Mirror</h2>
              <button
                type="button"
                className="rounded-xl border border-slate-300 px-3 py-1 text-xs"
                onClick={demo.refreshRuntimeState}
                disabled={!demo.sessionId}
              >
                Refresh Runtime
              </button>
            </div>
            {demo.runtimeScreenshot?.image_base64 ? (
              <div className="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                <img
                  src={`data:${demo.runtimeScreenshot.mime_type};base64,${demo.runtimeScreenshot.image_base64}`}
                  alt="Runtime screenshot"
                  className="h-auto w-full object-cover"
                />
              </div>
            ) : (
              <p className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                No runtime screenshot available yet. Start a live session and refresh runtime.
              </p>
            )}
            <div className="mt-3 space-y-1 text-sm text-slate-700">
              <p>URL: {demo.runtimeObservation?.observed_url ?? "n/a"}</p>
              <p>Title: {demo.runtimeObservation?.page_title ?? "n/a"}</p>
              <p>
                Hints:{" "}
                {demo.runtimeObservation?.detected_page_hints?.length
                  ? demo.runtimeObservation.detected_page_hints.join(", ")
                  : "n/a"}
              </p>
              <p>Cart items: {demo.runtimeObservation?.cart_item_count ?? "n/a"}</p>
              <p>
                Checkout ready:{" "}
                {demo.runtimeObservation?.checkout_ready === null ||
                demo.runtimeObservation?.checkout_ready === undefined
                  ? "n/a"
                  : demo.runtimeObservation.checkout_ready
                    ? "yes"
                    : "no"}
              </p>
              {demo.runtimeObservation?.notes ? (
                <p className="rounded-xl bg-slate-100 px-3 py-2">{demo.runtimeObservation.notes}</p>
              ) : null}
            </div>
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Session History</h2>
            <button
              type="button"
              className="mt-2 rounded-xl border border-slate-300 px-3 py-1 text-xs"
              onClick={demo.refreshSessionHistory}
            >
              Refresh
            </button>
            <div className="mt-3 max-h-64 overflow-y-auto rounded-2xl border border-slate-200">
              {demo.sessionHistory.length === 0 ? (
                <p className="p-3 text-sm text-slate-500">No sessions yet.</p>
              ) : (
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-100 text-xs uppercase tracking-wide text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Session</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demo.sessionHistory.map((item) => (
                      <tr key={item.session_id} className="border-t border-slate-200">
                        <td className="px-3 py-2 font-mono text-xs">{item.session_id.slice(0, 8)}...</td>
                        <td className="px-3 py-2">{formatSessionStatusLabel(item.status)}</td>
                        <td className="px-3 py-2">{formatDate(item.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </article>
        </aside>
      </div>
    </main>
  );
}
