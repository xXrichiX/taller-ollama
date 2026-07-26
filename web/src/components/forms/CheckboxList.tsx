import { FormField } from "./FormField";

export interface CheckboxListOption {
  id: number;
  label: string;
  meta?: string;
}

export function CheckboxList({
  label,
  hint,
  values,
  onChange,
  options,
  countLabel = "seleccionado(s)",
  className = "",
}: {
  label: string;
  hint?: string;
  values: number[];
  onChange: (values: number[]) => void;
  options: CheckboxListOption[];
  countLabel?: string;
  className?: string;
}) {
  const toggle = (id: number) => {
    onChange(
      values.includes(id)
        ? values.filter((v) => v !== id)
        : [...values, id],
    );
  };

  return (
    <FormField label={label} hint={hint} className={className}>
      <div className="checkbox-list">
        {values.length > 0 && (
          <p className="checkbox-list-summary">{values.length} {countLabel}</p>
        )}
        <div className="checkbox-list-items">
          {options.map((opt) => {
            const checked = values.includes(opt.id);
            return (
              <label key={opt.id} className={`checkbox-list-item${checked ? " is-checked" : ""}`}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(opt.id)}
                />
                <span className="checkbox-list-text">
                  <span className="checkbox-list-label">{opt.label}</span>
                  {opt.meta && <span className="checkbox-list-meta">{opt.meta}</span>}
                </span>
              </label>
            );
          })}
        </div>
      </div>
    </FormField>
  );
}
