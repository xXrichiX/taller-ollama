/** Clases visuales para estados de órdenes de servicio (citas). */

export function estadoPillClass(estadoLabel?: string): string {
  const label = (estadoLabel ?? "").toLowerCase();
  if (!label) return "status-pill";
  if (label.includes("espera") || label.includes("pendiente")) return "status-pill status-pill--wait";
  if (label.includes("recibido") || label.includes("diagn")) return "status-pill status-pill--info";
  if (label.includes("reparación") || label.includes("reparacion") || label.includes("proceso")) {
    return "status-pill status-pill--active";
  }
  if (label.includes("refaccion")) return "status-pill status-pill--warn";
  if (label.includes("finaliz") || label.includes("complet")) return "status-pill status-pill--done";
  if (label.includes("cancel")) return "status-pill status-pill--muted";
  return "status-pill";
}

export const ORDEN_ESTADOS_AYUDA =
  "Flujo: En espera → Recibido → Diagnóstico → En reparación → Esperando refacciones → Finalizado";
