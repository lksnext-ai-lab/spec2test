import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { Icon, type IconName } from './Icon';
import { Popover } from './Popover';

export interface Option {
  value: string;
  label: string;
  hint?: string;
  badges?: string[];
}

type Row = Option & { custom: boolean };

export interface DropdownAction {
  label: string;
  icon?: IconName;
  onSelect: () => void;
}

/** A searchable listbox: replaces the native <select>, with keyboard support. */
export function Dropdown(props: {
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  ariaLabel: string;
  placeholder?: string;
  searchable?: boolean;
  /** Lets the user type a value that is not in the list. */
  customLabel?: (query: string) => string;
  actions?: DropdownAction[];
  disabled?: boolean;
  leading?: ReactNode;
  emptyText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();

  const rows = useMemo((): Row[] => {
    const q = query.trim().toLowerCase();
    const shown = q ? props.options.filter((option) => `${option.label} ${option.hint ?? ''}`.toLowerCase().includes(q)) : props.options;
    const custom: Row[] = props.customLabel && q && !props.options.some((option) => option.value.toLowerCase() === q) ? [{ value: query.trim(), label: props.customLabel(query.trim()), custom: true }] : [];
    return [...shown.map((option) => ({ ...option, custom: false })), ...custom];
  }, [props.options, props.customLabel, query]);

  const selected = props.options.find((option) => option.value === props.value);
  const shownLabel = selected?.label ?? (props.value || props.placeholder || '');

  useEffect(() => {
    if (open) {
      setQuery('');
      setActive(Math.max(0, props.options.findIndex((option) => option.value === props.value)));
      requestAnimationFrame(() => input.current?.focus());
    }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  const choose = (value: string) => {
    props.onChange(value);
    close();
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((index) => Math.min(rows.length - 1, index + 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((index) => Math.max(0, index - 1));
    } else if (event.key === 'Enter' && rows[active]) {
      event.preventDefault();
      choose(rows[active].value);
    }
  };

  return (
    <Popover
      open={open}
      onClose={() => setOpen(false)}
      wide
      trigger={
        <button
          ref={trigger}
          type="button"
          className={`dropdown-trigger ${open ? 'is-open' : ''}`}
          aria-label={props.ariaLabel}
          aria-haspopup="listbox"
          aria-expanded={open}
          disabled={props.disabled}
          onClick={() => setOpen(!open)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown' && !open) {
              event.preventDefault();
              setOpen(true);
            }
          }}
        >
          {props.leading}
          <span className={`dropdown-value ${selected || props.value ? '' : 'placeholder'}`}>{shownLabel}</span>
          <Icon name="chevron-down" size={14} className="dropdown-caret" />
        </button>
      }
    >
      {props.searchable ? (
        <div className="dropdown-search">
          <Icon name="search" size={14} />
          <input
            ref={input}
            role="combobox"
            aria-expanded="true"
            aria-controls={`${id}-list`}
            aria-activedescendant={rows[active] ? `${id}-${active}` : undefined}
            aria-label={`Search ${props.ariaLabel}`}
            placeholder="Search…"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
          />
        </div>
      ) : (
        <input ref={input} className="sr-only" aria-label={props.ariaLabel} onKeyDown={onKeyDown} readOnly />
      )}
      <ul className="dropdown-list" role="listbox" id={`${id}-list`} aria-label={props.ariaLabel}>
        {rows.length === 0 ? <li className="dropdown-empty">{props.emptyText ?? 'Nothing found'}</li> : null}
        {rows.map((row, index) => (
          <li
            key={`${row.value}-${index}`}
            id={`${id}-${index}`}
            role="option"
            aria-selected={row.value === props.value}
            className={`dropdown-option ${index === active ? 'is-active' : ''} ${row.custom ? 'is-custom' : ''}`}
            onMouseMove={() => setActive(index)}
            onClick={() => choose(row.value)}
          >
            <span className="dropdown-check">{row.value === props.value ? <Icon name="check" size={14} /> : null}</span>
            <span className="dropdown-text">
              <span className="dropdown-label">{row.label}</span>
              {row.hint ? <span className="dropdown-hint">{row.hint}</span> : null}
            </span>
            {row.badges?.map((badge) => (
              <span className="tag" key={badge}>
                {badge}
              </span>
            ))}
          </li>
        ))}
      </ul>
      {props.actions?.length ? (
        <div className="dropdown-actions">
          {props.actions.map((action) => (
            <button
              key={action.label}
              type="button"
              className="menu-item"
              onClick={() => {
                setOpen(false);
                action.onSelect();
              }}
            >
              {action.icon ? <Icon name={action.icon} /> : null}
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </Popover>
  );
}
