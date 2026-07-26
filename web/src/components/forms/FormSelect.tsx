import { useEffect, useMemo, useRef, useState } from "react";
import { FormField } from "./FormField";

export interface FormSelectOption {
  value: string;
  label: string;
}

export function FormSelect({
  label,
  hint,
  value,
  onChange,
  options,
  placeholder = "Seleccionar",
  disabled = false,
  searchable = false,
  className = "",
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
  options: FormSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  searchable?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  const selected = options.find((o) => o.value === value);
  const showSearch = searchable && options.length > 6;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, query]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const pick = (next: string) => {
    onChange(next);
    setOpen(false);
    setQuery("");
  };

  return (
    <FormField label={label} hint={hint} className={className}>
      <div className={`form-select${open ? " is-open" : ""}`} ref={rootRef}>
        <button
          type="button"
          className={`form-select-trigger form-control${!value ? " is-placeholder" : ""}`}
          onClick={() => !disabled && setOpen((v) => !v)}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span className="form-select-value">{selected?.label ?? placeholder}</span>
          <svg className="form-select-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        {open && (
          <div className="form-select-menu" role="listbox">
            {showSearch && (
              <div className="form-select-search-wrap">
                <input
                  type="search"
                  className="form-select-search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Buscar…"
                  autoFocus
                />
              </div>
            )}
            <ul className="form-select-options">
              <li>
                <button
                  type="button"
                  className={`form-select-option${!value ? " is-selected" : ""}`}
                  onClick={() => pick("")}
                >
                  {placeholder}
                </button>
              </li>
              {filtered.map((o) => (
                <li key={o.value}>
                  <button
                    type="button"
                    className={`form-select-option${value === o.value ? " is-selected" : ""}`}
                    onClick={() => pick(o.value)}
                  >
                    {o.label}
                  </button>
                </li>
              ))}
              {filtered.length === 0 && (
                <li className="form-select-empty">Sin resultados</li>
              )}
            </ul>
          </div>
        )}
      </div>
    </FormField>
  );
}
