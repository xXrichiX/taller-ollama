export type AmPm = "AM" | "PM";

export interface TimeParts {
  hour12: number;
  minute: number;
  period: AmPm;
}

export function parseTimeValue(value: string): TimeParts {
  const parts = (value || "09:00").split(":");
  const h24 = Number.parseInt(parts[0] || "9", 10);
  const minute = Number.parseInt(parts[1] || "0", 10);
  const period: AmPm = h24 >= 12 ? "PM" : "AM";
  let hour12 = h24 % 12;
  if (hour12 === 0) hour12 = 12;
  return { hour12, minute: Number.isNaN(minute) ? 0 : minute, period };
}

export function toTimeString(parts: TimeParts, withSeconds = false): string {
  let h24 = parts.hour12 % 12;
  if (parts.period === "PM") h24 += 12;
  if (parts.period === "AM" && parts.hour12 === 12) h24 = 0;
  if (parts.period === "PM" && parts.hour12 === 12) h24 = 12;
  const base = `${String(h24).padStart(2, "0")}:${String(parts.minute).padStart(2, "0")}`;
  return withSeconds ? `${base}:00` : base;
}

export const HOURS_12 = Array.from({ length: 12 }, (_, i) => i + 1);
export const MINUTES = Array.from({ length: 60 }, (_, i) => i);

export function normalizeTimeValue(value: string, withSeconds = false): string {
  const parts = parseTimeValue(value);
  const base = toTimeString(parts, false);
  return withSeconds ? `${base}:00` : base;
}

export function buildTimeSlots(): Array<{ value: string; label: string }> {
  const slots: Array<{ value: string; label: string }> = [];
  for (let h = 7; h <= 19; h += 1) {
    for (const m of [0, 30]) {
      if (h === 19 && m > 0) break;
      const period: AmPm = h >= 12 ? "PM" : "AM";
      let h12 = h % 12;
      if (h12 === 0) h12 = 12;
      const value = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
      const label = `${h12}:${String(m).padStart(2, "0")} ${period === "AM" ? "a.m." : "p.m."}`;
      slots.push({ value, label });
    }
  }
  return slots;
}

export function buildTimeSlotsWithSeconds(): Array<{ value: string; label: string }> {
  return buildTimeSlots().map((s) => ({ value: `${s.value}:00`, label: s.label }));
}
