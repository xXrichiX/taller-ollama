import { useLayoutEffect, useState, type RefObject } from "react";

/** Abre el menú hacia arriba si no hay espacio debajo (p. ej. último campo del modal). */
export function useSelectDropUp(
  open: boolean,
  rootRef: RefObject<HTMLElement | null>,
  menuMaxHeight = 280,
) {
  const [dropUp, setDropUp] = useState(false);

  useLayoutEffect(() => {
    if (!open || !rootRef.current) {
      setDropUp(false);
      return;
    }
    const rect = rootRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    setDropUp(spaceBelow < menuMaxHeight && rect.top > spaceBelow);
  }, [open, menuMaxHeight, rootRef]);

  return dropUp;
}
