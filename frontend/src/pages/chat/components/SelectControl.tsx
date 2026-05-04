type Option = {
  value: string;
  label: string;
};

type Props = {
  label: string;
  value: string;
  ariaLabel: string;
  options: Option[];
  onChange: (value: string) => void;
};

export function SelectControl({ label, value, ariaLabel, options, onChange }: Props) {
  return (
    <div className="option-group">
      <span className="option-label">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="option-select"
        aria-label={ariaLabel}
      >
        {options.map((option) => (
          <option key={option.value || "auto"} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
