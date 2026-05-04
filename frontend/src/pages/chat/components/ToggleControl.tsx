type Props = {
  label: string;
  active: boolean;
  ariaLabel: string;
  title: string;
  onChange: (next: boolean) => void;
};

export function ToggleControl({ label, active, ariaLabel, title, onChange }: Props) {
  return (
    <div className="option-group">
      <span className="option-label">{label}</span>
      <button
        type="button"
        className={`option-toggle ${active ? "active" : ""}`}
        onClick={() => onChange(!active)}
        aria-label={ariaLabel}
        aria-pressed={active}
        title={title}
      >
        <span className="toggle-track">
          <span className="toggle-thumb"></span>
        </span>
      </button>
    </div>
  );
}
