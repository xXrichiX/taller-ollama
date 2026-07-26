import { useCallback, useState, type ReactNode } from "react";
import { Modal, ModalActions } from "./Modal";

function FilterIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M4 5h16l-6 7v6l-4 2v-8L4 5z" />
    </svg>
  );
}

export function useFilterModal<T extends Record<string, string>>(initial: T) {
  const [applied, setApplied] = useState<T>(initial);
  const [draft, setDraft] = useState<T>(initial);
  const [open, setOpen] = useState(false);

  const openFilter = useCallback(() => {
    setDraft({ ...applied });
    setOpen(true);
  }, [applied]);

  const cancelFilter = useCallback(() => {
    setDraft({ ...applied });
    setOpen(false);
  }, [applied]);

  const applyFilter = useCallback(() => {
    setApplied({ ...draft });
    setOpen(false);
  }, [draft]);

  const clearFilters = useCallback(() => {
    const empty = Object.fromEntries(Object.keys(initial).map((k) => [k, ""])) as T;
    setDraft(empty);
    setApplied(empty);
    setOpen(false);
  }, [initial]);

  const setDraftField = useCallback((key: keyof T, value: string) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }, []);

  const activeCount = Object.values(applied).filter(Boolean).length;
  const draftActiveCount = Object.values(draft).filter(Boolean).length;

  return {
    applied,
    draft,
    open,
    openFilter,
    cancelFilter,
    applyFilter,
    clearFilters,
    activeCount,
    draftActiveCount,
    setDraftField,
  };
}

export function ListFilter({
  open,
  activeCount,
  onOpen,
  onCancel,
  onSearch,
  onClear,
  draftActiveCount,
  children,
}: {
  open: boolean;
  activeCount: number;
  draftActiveCount?: number;
  onOpen: () => void;
  onCancel: () => void;
  onSearch: () => void;
  onClear: () => void;
  children: ReactNode;
}) {
  const showClear = (draftActiveCount ?? activeCount) > 0;
  return (
    <>
      <div className="list-filter">
        <button
          type="button"
          className={`list-filter-btn${activeCount > 0 ? " is-active" : ""}`}
          onClick={onOpen}
          aria-label="Filtros"
        >
          <span className="list-filter-icon-wrap">
            <FilterIcon />
          </span>
          <span className="list-filter-label">Filtros</span>
          {activeCount > 0 && (
            <span className="list-filter-badge">{activeCount}</span>
          )}
        </button>
      </div>

      <Modal
        open={open}
        wide
        title="Buscar por filtro"
        onClose={onCancel}
        footer={(
          <ModalActions
            onCancel={onCancel}
            onSave={onSearch}
            saveLabel="Buscar"
          />
        )}
      >
        <div className="filter-modal-grid form-grid form-grid-2col form-grid-spaced">
          {children}
        </div>
        {showClear && (
          <p className="filter-modal-clear">
            <button type="button" className="btn-text btn-text-sm" onClick={onClear}>
              Limpiar filtros
            </button>
          </p>
        )}
      </Modal>
    </>
  );
}

export function ListFilterSelect({
  label,
  value,
  onChange,
  options,
  placeholder = "TODO",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
}) {
  return (
    <div className="form-row">
      <label>{label}</label>
      <select
        className="form-control"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}

export function uniqueColumnValues<T>(
  rows: T[],
  getter: (row: T) => string | undefined | null,
): string[] {
  const set = new Set<string>();
  for (const row of rows) {
    const v = getter(row)?.trim();
    if (v) set.add(v);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "es"));
}
