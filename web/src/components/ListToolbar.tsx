import type { ReactNode } from "react";

export function ListToolbar({
  search,
  onSearchChange,
  placeholder = "Buscar…",
  action,
  onAdd,
  addLabel = "Nuevo",
  showSearch = true,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
  action?: ReactNode;
  onAdd?: () => void;
  addLabel?: string;
  showSearch?: boolean;
}) {
  return (
    <div className="list-toolbar">
      <div className="list-toolbar-spacer" />
      <div className="list-toolbar-actions">
        {showSearch && (
          <div className="search-group">
            <input
              type="search"
              className="search-input search-input-toolbar"
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={placeholder}
            />
            <button type="button" className="search-submit" aria-label="Buscar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3-3" />
              </svg>
            </button>
          </div>
        )}
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
