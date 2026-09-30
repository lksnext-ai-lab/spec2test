import type { DockerState } from '../shared/messages';

/** `detail` of a container that is running but does not answer on the published port. */
export const UNREACHABLE = 'unreachable';
export const UNREACHABLE_GRACE_MS = 30_000;

export interface Probe {
  state: DockerState;
  detail?: string;
}

/**
 * A container that is up but silent is "starting" for a grace period (it may just be
 * booting); after that it is "unhealthy", with the usual cause spelled out, instead of
 * showing "starting…" forever. `since` is when the silence began (undefined when it has not).
 */
export function judgeProbe(probe: Probe, since: number | undefined, now: number, port: number): { docker: Probe; since: number | undefined } {
  if (probe.detail !== UNREACHABLE) {
    return { docker: probe, since: undefined };
  }
  const start = since ?? now;
  if (now - start < UNREACHABLE_GRACE_MS) {
    return { docker: { state: 'starting' }, since: start };
  }
  return {
    docker: {
      state: 'unhealthy',
      detail: `The container is running but does not answer on port ${port}. An image built with an older version is the usual cause: press Rebuild.`,
    },
    since: start,
  };
}
