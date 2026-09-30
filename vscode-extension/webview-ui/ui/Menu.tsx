import { useEffect, useRef, useState } from 'react';
import { Icon, type IconName } from './Icon';
import { Popover } from './Popover';

export interface MenuItem {
  label: string;
  icon?: IconName;
  onSelect: () => void;
  danger?: boolean;
  disabled?: boolean;
  separatorBefore?: boolean;
}

export function Menu(props: { label: string; items: MenuItem[]; direction?: 'down' | 'up'; align?: 'start' | 'end'; icon?: IconName; className?: string; children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      list.current?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    }
  }, [open]);

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') {
      return;
    }
    event.preventDefault();
    const buttons = Array.from(list.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
    const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
    const next = event.key === 'ArrowDown' ? (index + 1) % buttons.length : (index - 1 + buttons.length) % buttons.length;
    buttons[next]?.focus();
  };

  return (
    <Popover
      open={open}
      onClose={() => setOpen(false)}
      direction={props.direction}
      align={props.align ?? 'end'}
      trigger={
        <button className={props.className ?? 'icon-btn'} aria-label={props.label} title={props.label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          {props.children ?? <Icon name={props.icon ?? 'more'} />}
        </button>
      }
    >
      <div className="menu" role="menu" ref={list} onKeyDown={onKeyDown}>
        {props.items.map((item) => (
          <div key={item.label}>
            {item.separatorBefore ? <div className="menu-sep" role="separator" /> : null}
            <button
              role="menuitem"
              className={`menu-item ${item.danger ? 'danger' : ''}`}
              disabled={item.disabled}
              onClick={() => {
                setOpen(false);
                item.onSelect();
              }}
            >
              {item.icon ? <Icon name={item.icon} /> : <span className="icon-gap" />}
              {item.label}
            </button>
          </div>
        ))}
      </div>
    </Popover>
  );
}
