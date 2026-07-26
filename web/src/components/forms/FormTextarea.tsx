import { FormField } from "./FormField";

export function FormTextarea({
  label,
  hint,
  value,
  onChange,
  placeholder,
  rows = 3,
  className = "",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
}) {
  return (
    <FormField label={label} hint={hint} className={className}>
      <textarea
        className="form-control"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
      />
    </FormField>
  );
}
