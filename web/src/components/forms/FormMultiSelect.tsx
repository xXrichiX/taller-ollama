import { useEffect, useMemo, useRef, useState } from "react";
import { FormField } from "./FormField";

export interface FormMultiSelectOption {
  value: string;
  label: string;
  meta?: string;
}

export function FormMultiSelect({
  label,
  values,
  onChange,
  options,
  placeholder = "Seleccionar",
  className = "",
}: {
  label: string;
  values: number[];
  onChange: (values: number[]) => void;
  options: FormMultiSelectOption[];
  placeholder?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = useMemo(
    () => options.filter((o) => values.includes(Number(o.value))),
    [options, values],
  );

  const triggerLabel = useMemo(() => {
    if (selected.length === 0) return placeholder;
    if (selected.length === 1) return selected[0].label;
    return `${selected.length} seleccionados`;
  }, [placeholder, selected]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const toggle = (id: number) => {
    onChange(
      values.includes(id)
        ? values.filter((v) => v !== id)
        : [...values, id],
    );
  };

  return (
    <FormField label={label} className={className}>
      <div className={`form-select${open ? " is-open" : ""}`} ref={rootRef}>
        <button
          type="button"
          className={`form-select-trigger form-control${selected.length === 0 ? " is-placeholder" : ""}`}
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span className="form-select-value">{triggerLabel}</span>
          <svg className="form-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        {open && (
          <div className="form-select-menu form-multi-select-menu">
            <ul className="form-multi-options">
              {options.map((o) => {
                const id = Number(o.value);
                const checked = values.includes(id);
                return (
                  <li key={o.value}>
                    <label className={`form-multi-option${checked ? " is-checked" : ""}`}>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(id)}
                      />
                      <span className="form-multi-label">{o.label}</span>
                      {o.meta && <span className="form-multi-meta">{o.meta}</span>}
                    </label>
                  </li>
                );
              })}
            </ul>
            <div className="form-multi-footer">
              <button type="button" className="btn-text" onClick={() => setOpen(false)}>
                Listo
              </button>
            </div>
          </div>
        )}
      </div>
    </FormField>
  );
}
