export function sanitizeInteger(value: string): string {
  return value.replace(/\D/g, "");
}

export function sanitizeDecimal(value: string): string {
  let next = value.replace(/[^\d.]/g, "");
  const dot = next.indexOf(".");
  if (dot !== -1) {
    next = `${next.slice(0, dot + 1)}${next.slice(dot + 1).replace(/\./g, "")}`;
  }
  return next;
}

export function sanitizePhone(value: string): string {
  return value.replace(/[^\d+\-() ]/g, "");
}

export function sanitizeInput(type: string, value: string): string {
  switch (type) {
    case "integer":
    case "tel":
      return type === "tel" ? sanitizePhone(value) : sanitizeInteger(value);
    case "number":
    case "decimal":
      return sanitizeDecimal(value);
    default:
      return value;
  }
}

export function parseDecimal(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed || trimmed === ".") return null;
  const n = Number(trimmed);
  return Number.isFinite(n) ? n : null;
}

export function parseInteger(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isFinite(n) || !Number.isInteger(n)) return null;
  return n;
}

export function isValidEmail(value: string): boolean {
  const email = value.trim();
  if (!email) return true;
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function isValidPhone(value: string): boolean {
  const phone = value.trim();
  if (!phone) return true;
  return /^[\d+\-() ]{7,20}$/.test(phone) && /\d/.test(phone);
}

export function requireText(value: string, label: string): string | null {
  if (!value.trim()) return `Indica ${label}.`;
  return null;
}

export function requireDecimal(value: string, label: string, min = 0): string | null {
  const n = parseDecimal(value);
  if (n === null) return `${label} debe ser un número válido.`;
  if (n < min) return `${label} no puede ser menor que ${min}.`;
  return null;
}

export function requireInteger(value: string, label: string, min = 0): string | null {
  const n = parseInteger(value);
  if (n === null) return `${label} debe ser un número entero válido.`;
  if (n < min) return `${label} no puede ser menor que ${min}.`;
  return null;
}
