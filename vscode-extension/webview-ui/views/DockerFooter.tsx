import type { AppState, DockerState } from '../../src/shared/messages';
import { Menu, type MenuItem } from '../ui/Menu';
import { Icon } from '../ui/Icon';
import { send } from '../vscode';

const LABEL: Record<DockerState, string> = {
  'no-repo': 'Not set up',
  'not-installed': 'Docker missing',
  'daemon-down': 'Docker off',
  stopped: 'Stopped',
  starting: 'Starting…',
  running: 'Running',
  unhealthy: 'Not responding',
};

type DockerAction = 'install' | 'startDocker' | 'start' | 'stop' | 'restart' | 'rebuild' | 'logs';
const act = (action: DockerAction) => () => send({ type: 'docker', action });

/** The one action that fixes the current state. */
export function primaryAction(state: AppState): { label: string; run: () => void } | undefined {
  switch (state.docker.state) {
    case 'no-repo':
      return { label: 'Choose spec2test folder', run: () => send({ type: 'chooseRepo' }) };
    case 'not-installed':
      return { label: 'Get Docker', run: act('install') };
    case 'daemon-down':
      return { label: 'Start Docker', run: act('startDocker') };
    case 'stopped':
      return { label: 'Start input-processor', run: act('start') };
    case 'unhealthy':
      return { label: 'Rebuild and restart', run: act('rebuild') };
    default:
      return undefined;
  }
}

function menuFor(state: AppState): MenuItem[] {
  const logs: MenuItem = { label: 'Show logs', icon: 'terminal', onSelect: act('logs') };
  switch (state.docker.state) {
    case 'running':
      return [
        { label: 'Restart', icon: 'refresh', onSelect: act('restart') },
        { label: 'Stop', icon: 'stop', onSelect: act('stop') },
        { label: 'Rebuild image', icon: 'container', onSelect: act('rebuild') },
        { ...logs, separatorBefore: true },
      ];
    case 'unhealthy':
      return [
        { label: 'Rebuild and restart', icon: 'container', onSelect: act('rebuild') },
        { label: 'Restart', icon: 'refresh', onSelect: act('restart') },
        { label: 'Stop', icon: 'stop', onSelect: act('stop') },
        { ...logs, separatorBefore: true },
      ];
    case 'starting':
      return [logs];
    case 'stopped':
      return [
        { label: 'Start', icon: 'play', onSelect: act('start') },
        { label: 'Rebuild image', icon: 'container', onSelect: act('rebuild') },
        { ...logs, separatorBefore: true },
      ];
    case 'daemon-down':
      return [{ label: 'Start Docker', icon: 'power', onSelect: act('startDocker') }];
    case 'not-installed':
      return [{ label: 'Get Docker', icon: 'external', onSelect: act('install') }];
    default:
      return [{ label: 'Choose spec2test folder…', icon: 'folder', onSelect: () => send({ type: 'chooseRepo' }) }];
  }
}

export function DockerFooter({ state }: { state: AppState }) {
  const { docker } = state;
  const shown: DockerState = docker.busy ? 'starting' : docker.state;
  return (
    <footer className="footer">
      {docker.busy ? <div className="bar indeterminate footer-bar" /> : null}
      <Menu label="Input-processor: container controls" items={menuFor(state)} direction="up" align="start" className="docker-btn">
        <Icon name="container" />
        <span className={`dot dot-${shown}`} aria-hidden="true" />
        <span className="docker-label">{docker.busy ?? LABEL[docker.state]}</span>
        <Icon name="chevron-up" size={12} />
      </Menu>
      <span className="footer-note muted">Input-processor</span>
    </footer>
  );
}
