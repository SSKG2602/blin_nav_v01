"use client";

type VoiceMicButtonProps = {
  listening: boolean;
  disabled?: boolean;
  onPress: () => void;
};

export function VoiceMicButton({ listening, disabled = false, onPress }: VoiceMicButtonProps) {
  return (
    <button
      type="button"
      onClick={onPress}
      disabled={disabled}
      aria-label={listening ? "Stop voice capture" : "Start voice capture"}
      aria-pressed={listening}
      className={`relative grid h-32 w-32 place-items-center rounded-full border-4 border-white text-white shadow-lg transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-300 sm:h-36 sm:w-36 ${
        listening
          ? "animate-glow-pulse bg-emerald-600"
          : "bg-slate-800 hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
      }`}
    >
      {listening ? <span className="absolute h-full w-full animate-ring rounded-full border border-emerald-300" /> : null}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
        className="h-10 w-10"
        stroke="currentColor"
        strokeWidth={1.8}
      >
        <path d="M12 3v10m0 0a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v3a3 3 0 0 0 3 3Zm0 0v4m-4 0h8" />
      </svg>
    </button>
  );
}
