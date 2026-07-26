import type { ReactNode } from "react";

export function ListToolbar({
  search,
  onSearchChange,
  placeholder = "Buscar…",
  action,
  onAdd,
  addLabel = "Nuevo",
}: {
  search: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
  action?: ReactNode;
  onAdd?: () => void;
  addLabel?: string;
}) {
  return (
    <div className="list-toolbar">
      <div className="search-field">
        <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3-3" />
        </svg>
        <input
          type="search"
          className="search-input"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
        />
      </div>
      <div className="list-toolbar-actions">
        {action}
        {onAdd && (
          <button type="button" className="btn-add" onClick={onAdd} title={addLabel} aria-label={addLabel}>
            +
          </button>
        )}
      </div>
    </div>
  );
}
