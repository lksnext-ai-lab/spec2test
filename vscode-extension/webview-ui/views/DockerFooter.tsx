import type { AppState, DockerState } from '../../src/shared/messages';
import { Menu, type MenuItem } from '../ui/Menu';
import { Icon } from '../ui/Icon';
import { send } from '../vscode';

const LABEL: Record<DockerState, string> = {
  'not-installed': 'Docker missing',
  'daemon-down': 'Docker off',
  stopped: 'Stopped',
  starting: 'Starting…',
  running: 'Running',
  outdated: 'Update available',
  unhealthy: 'Not responding',
};

type DockerAction = 'install' | 'startDocker' | 'start' | 'stop' | 'restart' | 'rebuild' | 'logs' | 'crawlerLogs';
const act = (action: DockerAction) => () => send({ type: 'docker', action });

/** The one action that fixes the current state. */
export function primaryAction(state: AppState): { label: string; run: () => void } | undefined {
  switch (state.docker.state) {
    case 'not-installed':
      return { label: 'Get Docker', run: act('install') };
    case 'daemon-down':
      return { label: 'Start Docker', run: act('startDocker') };
    case 'stopped':
      return { label: 'Start input-processor', run: act('start') };
    case 'unhealthy':
    case 'outdated':
      return { label: 'Update image and restart', run: act('rebuild') };
    default:
      return undefined;
  }
}

function menuFor(state: AppState): MenuItem[] {
  const logs: MenuItem = { label: 'Show logs', icon: 'terminal', onSelect: act('logs') };
  const crawlerLogs: MenuItem[] = state.crawler ? [{ label: 'Show web-crawler logs', icon: 'terminal', onSelect: act('crawlerLogs') }] : [];
  switch (state.docker.state) {
    case 'running':
      return [
        { label: 'Restart', icon: 'refresh', onSelect: act('restart') },
        { label: 'Stop', icon: 'stop', onSelect: act('stop') },
        { label: 'Update image', icon: 'container', onSelect: act('rebuild') },
        { ...logs, separatorBefore: true },
        ...crawlerLogs,
      ];
    case 'outdated':
    case 'unhealthy':
      return [
        { label: 'Update image and restart', icon: 'container', onSelect: act('rebuild') },
        { label: 'Restart', icon: 'refresh', onSelect: act('restart') },
        { label: 'Stop', icon: 'stop', onSelect: act('stop') },
        { ...logs, separatorBefore: true },
      ];
    case 'starting':
      return [logs];
    case 'stopped':
      return [
        { label: 'Start', icon: 'play', onSelect: act('start') },
        { label: 'Update image', icon: 'container', onSelect: act('rebuild') },
        { ...logs, separatorBefore: true },
      ];
    case 'daemon-down':
      return [{ label: 'Start Docker', icon: 'power', onSelect: act('startDocker') }];
    case 'not-installed':
      return [{ label: 'Get Docker', icon: 'external', onSelect: act('install') }];
    default:
      return [logs];
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
      <span className="footer-note muted" title={state.crawler?.detail}>
        {state.crawler ? (
          <>
            <span className={`dot dot-${state.crawler.state}`} aria-hidden="true" /> Crawler {LABEL[state.crawler.state].toLowerCase()}
          </>
        ) : (
          'Input-processor'
        )}
      </span>
    </footer>
  );
}
