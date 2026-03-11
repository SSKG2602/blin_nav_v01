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
  const clarificationPending = demo.clarificationPending;
  const finalConfirmation = demo.finalConfirmation;
  const finalConfirmationPending = demo.finalConfirmationPending;
  const postPurchase = demo.context?.latest_post_purchase_summary;
  const cartSnapshot = demo.context?.latest_cart_snapshot;
  const latestOrder = demo.context?.latest_order_snapshot;
  const finalArtifact = demo.context?.latest_final_session_artifact;
  const finalDiagnosis = demo.context?.latest_final_self_diagnosis;
  const connectionState = demo.connected ? "connected" : demo.connecting ? "connecting" : "disconnected";
  const navigationStep =
    demo.context?.latest_multimodal_assessment?.recommended_next_step ??
    demo.context?.latest_multimodal_assessment?.decision ??
    "No recommended step yet";
  const micDisabled = !demo.speechSupported;
  const micTooltip = !demo.speechSupported
    ? "Voice recognition requires Chrome or Edge browser"
    : demo.voiceModeEnabled
      ? "Disable voice listening"
      : "Enable voice listening";
  const sessionButtonLabel = demo.sessionId ? "Session Active" : demo.connecting ? "Starting Session..." : "Start Session";
  const voiceButtonLabel = demo.voiceModeEnabled ? "Disable Voice" : "Enable Voice";

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
            {clarificationPending ? (
              <span className="rounded-full border border-cyan-300 bg-cyan-50 px-3 py-1 font-medium text-cyan-900">
                Clarification Pending
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
          <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Demo Identity
                </h2>
                {demo.currentUser ? (
                  <p className="mt-1 text-sm text-slate-700">
                    Signed in as <span className="font-medium">{demo.currentUser.display_name}</span> ({demo.currentUser.email})
                  </p>
                ) : (
                  <p className="mt-1 text-sm text-slate-600">
                    Guest mode is active. Sign in to persist personalized session history.
                  </p>
                )}
              </div>
              {demo.currentUser ? (
                <button
                  type="button"
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm"
                  onClick={demo.logoutUser}
                >
                  Sign Out
                </button>
              ) : null}
            </div>
            {demo.currentUser ? null : (
              <div className="mt-4 grid gap-3 md:grid-cols-[auto_1fr_1fr_1fr_auto]">
                <div className="flex items-center gap-2 text-sm">
                  <button
                    type="button"
                    className={`rounded-xl px-3 py-2 ${demo.authMode === "login" ? "bg-slate-900 text-white" : "border border-slate-300 bg-white"}`}
                    onClick={() => demo.setAuthMode("login")}
                  >
                    Login
                  </button>
                  <button
                    type="button"
                    className={`rounded-xl px-3 py-2 ${demo.authMode === "signup" ? "bg-slate-900 text-white" : "border border-slate-300 bg-white"}`}
                    onClick={() => demo.setAuthMode("signup")}
                  >
                    Signup
                  </button>
                </div>
                {demo.authMode === "signup" ? (
                  <input
                    value={demo.authDisplayName}
                    onChange={(event) => demo.setAuthDisplayName(event.target.value)}
                    placeholder="Display name"
                    className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
                  />
                ) : (
                  <div className="hidden md:block" />
                )}
                <input
                  value={demo.authEmail}
                  onChange={(event) => demo.setAuthEmail(event.target.value)}
                  placeholder="Email"
                  className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
                />
                <input
                  value={demo.authPassword}
                  onChange={(event) => demo.setAuthPassword(event.target.value)}
                  placeholder="Password"
                  type="password"
                  className="rounded-xl border border-slate-300 px-3 py-2 text-sm"
                />
                <button
                  type="button"
                  className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
                  onClick={demo.authMode === "signup" ? demo.signupUser : demo.loginUser}
                  disabled={demo.authBusy}
                >
                  {demo.authBusy ? "Working..." : demo.authMode === "signup" ? "Create Account" : "Sign In"}
                </button>
              </div>
            )}
            <div className="mt-3 rounded-2xl border border-slate-200 bg-slate-100 p-3 text-sm text-slate-700">
              <p className="font-medium text-slate-900">Bounded demo merchant: demo.nopcommerce.com</p>
              <p className="mt-1">
                The public demo opens directly on the nopCommerce demo storefront. No cookie export or merchant connect step is required.
              </p>
            </div>
          </div>
        </section>

        <section className="space-y-5">
          <article className="rounded-3xl border border-slate-300 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Voice Controls</h2>
            <p className="mt-1 text-sm text-slate-600">
              Start the session, enable voice once, and keep commands simple.
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
                disabled={demo.connecting || Boolean(demo.sessionId)}
              >
                {sessionButtonLabel}
              </button>
              <div className="flex items-center justify-center md:justify-start" title={micTooltip}>
                <div className="flex items-center gap-3">
                  <VoiceMicButton
                    listening={demo.voiceModeEnabled || demo.listening}
                    disabled={micDisabled}
                    onPress={demo.voiceModeEnabled ? demo.disableVoiceMode : demo.enableVoiceMode}
                  />
                  <span className="text-sm font-medium text-slate-700">{voiceButtonLabel}</span>
                </div>
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
              <span className={`rounded-full px-3 py-1 ${demo.voiceModeEnabled ? "bg-emerald-100 text-emerald-900" : "bg-slate-100"}`}>
                Voice: {demo.voiceModeEnabled ? "enabled" : "disabled"}
              </span>
              <span className={`rounded-full px-3 py-1 ${demo.listening ? "bg-teal-100 text-teal-900" : "bg-slate-100"}`}>
                Listening: {demo.listening ? "yes" : "no"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Session: {demo.sessionId ? "active" : "idle"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Audio capture: {demo.audioCaptureSupported ? "available" : "unavailable"}
              </span>
              <span className="rounded-full bg-slate-100 px-3 py-1">
                Playback: {demo.speaking ? "Speaking..." : "idle"}
              </span>
              <button
                type="button"
                className="rounded-xl border border-slate-400 px-4 py-2 text-sm font-medium disabled:border-slate-200 disabled:text-slate-400"
                onClick={demo.sendCancel}
                disabled={!demo.connected}
              >
                Stop Current Task
              </button>
              <button
                type="button"
                className="rounded-xl border border-rose-400 px-4 py-2 text-sm font-medium text-rose-700 disabled:border-slate-200 disabled:text-slate-400"
                onClick={demo.closeConnection}
                disabled={!demo.sessionId}
              >
                Cancel Session
              </button>
            </div>
            <p className="mt-3 text-sm text-slate-600">
              Say commands like <span className="font-medium">Luminar start session</span>,{" "}
              <span className="font-medium">find build your own computer</span>, or{" "}
              <span className="font-medium">cancel it</span>.
            </p>
            {demo.voiceSupportMessage ? (
              <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                {demo.voiceSupportMessage}
              </p>
            ) : null}
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
            <h2 className="text-lg font-semibold">Clarification / Checkpoint / Final Confirmation</h2>
            {clarificationPending ? (
              <div className="mt-3 space-y-3 rounded-2xl border border-cyan-200 bg-cyan-50 p-3">
                <p className="text-sm font-medium text-cyan-950">
                  {demo.clarification?.prompt_to_user ?? "Clarification is required before continuing."}
                </p>
                {demo.clarification?.candidate_summary ? (
                  <p className="text-sm text-cyan-900">{demo.clarification.candidate_summary}</p>
                ) : null}
                {demo.clarification?.candidate_options?.length ? (
                  <div className="space-y-2">
                    {demo.clarification.candidate_options.map((option) => (
                      <div key={option.label} className="rounded-xl border border-cyan-200 bg-white/70 p-2 text-sm text-cyan-950">
                        <p className="font-medium">{option.label}: {option.title}</p>
                        <p className="text-xs text-cyan-900">
                          {option.price_text ?? "price n/a"} | {option.variant_text ?? "variant n/a"}
                        </p>
                        {option.difference_summary ? (
                          <p className="text-xs text-cyan-900">{option.difference_summary}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
                {demo.clarification?.expected_fields?.length ? (
                  <p className="text-xs text-cyan-900">
                    Missing or uncertain fields:{" "}
                    <span className="font-mono">{demo.clarification.expected_fields.join(", ")}</span>
                  </p>
                ) : null}
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded-xl bg-cyan-700 px-4 py-2 text-sm font-medium text-white"
                    onClick={() => demo.respondToClarification(true)}
                    disabled={!demo.connected}
                  >
                    Approve / Continue
                  </button>
                  <button
                    type="button"
                    className="rounded-xl border border-cyan-500 px-4 py-2 text-sm font-medium text-cyan-900"
                    onClick={() => demo.respondToClarification(false)}
                    disabled={!demo.connected}
                  >
                    Reject
                  </button>
                </div>
                <p className="text-xs text-cyan-900/80">
                  You can also answer by typing or speaking a more specific clarification.
                </p>
              </div>
            ) : null}
            {checkpointPending ? (
                <div className="mt-3 space-y-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-amber-800">
                    Checkpoint kind: {demo.checkpoint?.kind ?? "UNKNOWN"}
                  </p>
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
              {clarificationPending ? (
                <p className="rounded-xl border border-cyan-300 bg-cyan-50 px-3 py-2 text-sm text-cyan-900">
                  A clarification boundary is active and the backend is waiting for a bounded user response.
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
              !clarificationPending &&
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
            {demo.context?.latest_review_assessment ? (
              <div className="mt-3 rounded-2xl bg-slate-50 p-3 text-sm text-slate-700">
                <p className="font-medium">Review takeaway</p>
                <p className="mt-1">{demo.context.latest_review_assessment.review_summary_spoken}</p>
                {demo.context.latest_review_assessment.positive_signals.length ? (
                  <p className="mt-2 text-xs text-emerald-800">
                    Positives: {demo.context.latest_review_assessment.positive_signals.join(" | ")}
                  </p>
                ) : null}
                {demo.context.latest_review_assessment.negative_signals.length ? (
                  <p className="mt-1 text-xs text-rose-800">
                    Negatives: {demo.context.latest_review_assessment.negative_signals.join(" | ")}
                  </p>
                ) : null}
              </div>
            ) : null}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Current Session Evidence</h2>
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
              <p className="mt-3 text-sm text-slate-600">No current session evidence captured yet.</p>
            )}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Browser Activity</h2>
            <p className="mt-2 text-sm text-slate-600">{demo.browserActivityStatus}</p>
            <div className="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
              {demo.runtimeScreenshot?.image_base64 ? (
                <img
                  src={`data:${demo.runtimeScreenshot.mime_type};base64,${demo.runtimeScreenshot.image_base64}`}
                  alt="Live browser activity"
                  className="h-auto w-full object-cover"
                />
              ) : (
                <div className="flex min-h-48 items-center justify-center px-4 py-6 text-sm text-slate-500">
                  {demo.runtimeScreenshot?.notes ?? "Waiting for the live browser thumbnail."}
                </div>
              )}
            </div>
            <p className="mt-3 text-sm text-slate-700">
              URL: {demo.runtimeObservation?.observed_url ?? "n/a"}
            </p>
            {demo.runtimeScreenshot?.notes ? (
              <p className="mt-1 text-xs text-slate-500">{demo.runtimeScreenshot.notes}</p>
            ) : null}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Cart Context</h2>
            {cartSnapshot?.items?.length ? (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-slate-600">
                  Items: {cartSnapshot.cart_item_count ?? cartSnapshot.items.length} | Checkout ready:{" "}
                  {cartSnapshot.checkout_ready === true
                    ? "yes"
                    : cartSnapshot.checkout_ready === false
                      ? "no"
                      : "unknown"}
                </p>
                {cartSnapshot.items.map((item) => (
                  <div key={item.item_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm">
                    {(() => {
                      const parsedQuantity = Number.parseInt(item.quantity_text ?? "1", 10);
                      const quantityValue = Number.isFinite(parsedQuantity) ? parsedQuantity : 1;
                      return (
                        <>
                    <p className="font-medium text-slate-900">{item.title ?? item.item_id}</p>
                    <p className="text-slate-600">
                      {item.price_text ?? "price n/a"} | {item.quantity_text ?? "qty n/a"} | {item.variant_text ?? "variant n/a"}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className="rounded-xl border border-slate-300 px-3 py-1 text-xs"
                        onClick={() =>
                          demo.updateCartLineQuantity(
                            Math.max(1, quantityValue - 1),
                            item.item_id,
                            item.title
                          )
                        }
                      >
                        Qty -
                      </button>
                      <button
                        type="button"
                        className="rounded-xl border border-slate-300 px-3 py-1 text-xs"
                        onClick={() =>
                          demo.updateCartLineQuantity(
                            Math.max(1, quantityValue + 1),
                            item.item_id,
                            item.title
                          )
                        }
                      >
                        Qty +
                      </button>
                      <button
                        type="button"
                        className="rounded-xl border border-rose-300 px-3 py-1 text-xs font-medium text-rose-700"
                        onClick={() => demo.removeCartLine(item.item_id, item.title)}
                      >
                        Remove Item
                      </button>
                    </div>
                        </>
                      );
                    })()}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No cart items captured yet.</p>
            )}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Deferred Order Snapshot</h2>
                <p className="mt-1 text-xs text-slate-500">Not part of the bounded nopCommerce demo path.</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded-xl border border-slate-300 px-3 py-1 text-xs"
                  onClick={demo.fetchLatestOrderSnapshot}
                  disabled={!demo.sessionId}
                >
                  Load Deferred Order
                </button>
                {(postPurchase || latestOrder) ? (
                  <button
                    type="button"
                    className="rounded-xl border border-rose-300 px-3 py-1 text-xs font-medium text-rose-700 disabled:border-slate-200 disabled:text-slate-400"
                    onClick={demo.cancelPlacedOrder}
                    disabled={!demo.sessionId || demo.orderCancelBusy}
                  >
                    {demo.orderCancelBusy ? "Cancelling..." : "Cancel Deferred Order"}
                  </button>
                ) : null}
              </div>
            </div>
            {latestOrder ? (
              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>Order: {latestOrder.order_card_title ?? latestOrder.order_id_hint ?? "n/a"}</p>
                <p>Date: {latestOrder.order_date_text ?? "n/a"}</p>
                <p>Status: {latestOrder.shipping_stage_text ?? "n/a"}</p>
                <p>Expected delivery: {latestOrder.expected_delivery_text ?? "n/a"}</p>
                <p>Total: {latestOrder.order_total_text ?? "n/a"}</p>
                <p>Returns: {latestOrder.returns_entry_hint ?? "n/a"}</p>
                <p>Support: {latestOrder.support_entry_hint ?? "n/a"}</p>
                <p className="rounded-xl bg-slate-100 px-3 py-2">{latestOrder.spoken_summary}</p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No deferred order snapshot loaded.</p>
            )}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Final Session Artifact</h2>
            {finalArtifact ? (
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                <p>Original goal: {finalArtifact.original_goal ?? "n/a"}</p>
                <p>Clarified goal: {finalArtifact.clarified_goal ?? "n/a"}</p>
                <p>Chosen product: {finalArtifact.chosen_product ?? "n/a"}</p>
                <p>Chosen variant: {finalArtifact.chosen_variant ?? "n/a"}</p>
                <p>Merchant: {finalArtifact.merchant ?? "n/a"}</p>
                <p>Trust status: {finalArtifact.trust_status ?? "n/a"}</p>
                {finalArtifact.warnings.length ? (
                  <div className="rounded-xl bg-amber-50 px-3 py-2 text-amber-900">
                    Warnings: {finalArtifact.warnings.join(" | ")}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No final session artifact recorded yet.</p>
            )}
          </article>

          <article className="rounded-3xl border border-slate-300 bg-white p-5">
            <h2 className="text-lg font-semibold">Final Self-Diagnosis</h2>
            {finalDiagnosis ? (
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                <p>
                  Ready to close:{" "}
                  <span className="font-medium">{finalDiagnosis.ready_to_close ? "yes" : "no"}</span>
                </p>
                <p className="rounded-xl bg-slate-100 px-3 py-2">{finalDiagnosis.summary}</p>
                {finalDiagnosis.unresolved_items.length ? (
                  <p>Unresolved: {finalDiagnosis.unresolved_items.join(", ")}</p>
                ) : null}
                {finalDiagnosis.fallback_heavy_steps.length ? (
                  <p>Fallback-heavy steps: {finalDiagnosis.fallback_heavy_steps.join(", ")}</p>
                ) : null}
                {finalDiagnosis.confidence_warnings.length ? (
                  <p>Confidence warnings: {finalDiagnosis.confidence_warnings.join(" | ")}</p>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">No final self-diagnosis recorded yet.</p>
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
                      <th className="px-3 py-2">Owner</th>
                      <th className="px-3 py-2">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demo.sessionHistory.map((item) => (
                      <tr key={item.session_id} className="border-t border-slate-200">
                        <td className="px-3 py-2 font-mono text-xs">{item.session_id.slice(0, 8)}...</td>
                        <td className="px-3 py-2">{formatSessionStatusLabel(item.status)}</td>
                        <td className="px-3 py-2">{item.owner_display_name ?? "guest"}</td>
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
