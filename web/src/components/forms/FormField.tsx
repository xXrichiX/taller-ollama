import type { ReactNode } from "react";

export function FormField({
  label,
  hint,
  children,
  className = "",
}: {
  label: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`form-row ${className}`.trim()}>
      <label>{label}</label>
      {hint && <p className="form-hint">{hint}</p>}
      {children}
    </div>
  );
}
