import { useEffect, useRef, type ReactNode, type RefObject } from 'react';

/** Close a popover on outside press or Escape. */
export function useDismiss(open: boolean, close: () => void, ref: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onPointer = (event: PointerEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        close();
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        close();
      }
    };
    document.addEventListener('pointerdown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, close, ref]);
}

export function Popover(props: { open: boolean; onClose: () => void; trigger: ReactNode; direction?: 'down' | 'up'; align?: 'start' | 'end'; wide?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(props.open, props.onClose, ref);
  return (
    <div className="popover-anchor" ref={ref}>
      {props.trigger}
      {props.open ? (
        <div className={`popover popover-${props.direction ?? 'down'} popover-${props.align ?? 'start'} ${props.wide ? 'popover-wide' : ''}`}>{props.children}</div>
      ) : null}
    </div>
  );
}
