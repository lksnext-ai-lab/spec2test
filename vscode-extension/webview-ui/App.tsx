import { Component, useEffect, useState, type ErrorInfo, type ReactNode } from 'react';
import type { AppState, ToWebview } from '../src/shared/messages';
import { MainView } from './views/MainView';
import { SettingsView, type Tab } from './views/SettingsView';
import { send, vscode } from './vscode';

interface Saved {
  view: 'main' | 'settings';
  tab: Tab;
}

const TABS: Tab[] = ['models', 'environment', 'video', 'advanced'];

/** State saved by an older version of the sidebar may have another shape: never trust it. */
function restore(saved: Partial<Saved> | undefined): Saved {
  return {
    view: saved?.view === 'settings' ? 'settings' : 'main',
    tab: TABS.includes(saved?.tab as Tab) ? (saved?.tab as Tab) : 'models',
  };
}

/** A render error must never leave the sidebar blank with no explanation. */
class Boundary extends Component<{ children: ReactNode }, { error?: Error }> {
  state: { error?: Error } = {};

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Spec2Test sidebar crashed', error, info.componentStack);
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }
    return (
      <div className="empty" role="alert">
        <h3>Something went wrong</h3>
        <p className="muted small mono">{this.state.error.message}</p>
        <button
          className="primary"
          onClick={() => {
            vscode.setState<Saved>({ view: 'main', tab: 'models' });
            this.setState({ error: undefined });
            send({ type: 'ready' });
          }}
        >
          Try again
        </button>
      </div>
    );
  }
}

export function App() {
  return (
    <Boundary>
      <Screens />
    </Boundary>
  );
}

function Screens() {
  const [state, setState] = useState<AppState | undefined>();
  const [ui, setUi] = useState<Saved>(() => restore(vscode.getState<Partial<Saved>>()));

  useEffect(() => {
    const listener = (event: MessageEvent<ToWebview>) => {
      if (event.data.type === 'state') {
        setState(event.data.state);
      }
    };
    window.addEventListener('message', listener);
    send({ type: 'ready' });
    return () => window.removeEventListener('message', listener);
  }, []);

  // Braces matter: setState returns the state, and an effect must not return a non-function.
  useEffect(() => {
    vscode.setState<Saved>(ui);
  }, [ui]);

  if (!state) {
    return <p className="muted center pad">Loading…</p>;
  }
  return ui.view === 'settings' ? (
    <SettingsView state={state} tab={ui.tab} setTab={(tab) => setUi({ ...ui, tab })} back={() => setUi({ ...ui, view: 'main' })} />
  ) : (
    <MainView state={state} openSettings={() => setUi({ ...ui, view: 'settings' })} />
  );
}
