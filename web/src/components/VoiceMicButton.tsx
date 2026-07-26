interface VoiceMicButtonProps {
  listening: boolean;
  disabled?: boolean;
  onClick: () => void;
  title: string;
}

export function VoiceMicButton({ listening, disabled, onClick, title }: VoiceMicButtonProps) {
  return (
    <button
      type="button"
      className={`voice-btn${listening ? " listening" : ""}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={title}
      title={title}
    >
      <span className="voice-btn-ring" aria-hidden />
      {listening ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 15a3 3 0 003-3V6a3 3 0 10-6 0v6a3 3 0 003 3z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
          <path
            d="M19 11a7 7 0 01-14 0M12 18v3M8 21h8"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
      )}
    </button>
  );
}
