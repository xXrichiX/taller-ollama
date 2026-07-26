import { FormField } from "./FormField";

export function FormInput({
  label,
  hint,
  value,
  onChange,
  type = "text",
  placeholder,
  disabled = false,
  autoFocus = false,
  className = "",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  className?: string;
}) {
  return (
    <FormField label={label} hint={hint} className={className}>
      <input
        className="form-control"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
      />
    </FormField>
  );
}
