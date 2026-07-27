import { FormField } from "./FormField";
import { sanitizeInput } from "../../utils/formValidation";

type FormInputType = "text" | "email" | "password" | "number" | "decimal" | "integer" | "tel" | "date";

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
  type?: FormInputType;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  className?: string;
}) {
  const isNumeric = type === "number" || type === "decimal" || type === "integer";
  const htmlType = isNumeric || type === "tel" ? "text" : type;
  const inputMode =
    type === "integer" ? "numeric"
      : isNumeric ? "decimal"
        : type === "tel" ? "tel"
          : type === "email" ? "email"
            : undefined;

  const handleChange = (raw: string) => {
    onChange(sanitizeInput(type, raw));
  };

  return (
    <FormField label={label} hint={hint} className={className}>
      <input
        className="form-control"
        type={htmlType}
        inputMode={inputMode}
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        autoComplete={type === "email" ? "email" : type === "tel" ? "tel" : undefined}
      />
    </FormField>
  );
}
