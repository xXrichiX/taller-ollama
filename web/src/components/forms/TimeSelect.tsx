import { useMemo } from "react";
import { FormSelect } from "./FormSelect";
import { buildTimeSlots, buildTimeSlotsWithSeconds, normalizeTimeValue } from "../../utils/time";

export function TimeSelect({
  label,
  value,
  onChange,
  withSeconds = false,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  withSeconds?: boolean;
  className?: string;
}) {
  const slots = useMemo(
    () => (withSeconds ? buildTimeSlotsWithSeconds() : buildTimeSlots()),
    [withSeconds],
  );

  const normalized = normalizeTimeValue(value, withSeconds);
  const selectValue = slots.some((s) => s.value === normalized)
    ? normalized
    : slots[0]?.value ?? "";

  return (
    <FormSelect
      label={label}
      value={selectValue}
      onChange={onChange}
      options={slots}
      placeholder="Seleccionar hora"
      className={className}
    />
  );
}
