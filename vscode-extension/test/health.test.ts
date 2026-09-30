import { describe, expect, it } from 'vitest';
import { UNREACHABLE, UNREACHABLE_GRACE_MS, judgeProbe } from '../src/core/health';

const silent = { state: 'starting' as const, detail: UNREACHABLE };

describe('judgeProbe (a running container that does not answer)', () => {
  it('passes ordinary probes through and forgets any earlier silence', () => {
    expect(judgeProbe({ state: 'running' }, 1000, 5000, 8003)).toEqual({ docker: { state: 'running' }, since: undefined });
    expect(judgeProbe({ state: 'stopped' }, undefined, 5000, 8003).since).toBeUndefined();
  });

  it('is "starting" while the silence is young, and remembers when it began', () => {
    const first = judgeProbe(silent, undefined, 10_000, 8003);
    expect(first).toEqual({ docker: { state: 'starting' }, since: 10_000 });
    expect(judgeProbe(silent, first.since, 10_000 + UNREACHABLE_GRACE_MS - 1, 8003).docker.state).toBe('starting');
  });

  it('becomes unhealthy after the grace period, naming the port and the fix', () => {
    const result = judgeProbe(silent, 10_000, 10_000 + UNREACHABLE_GRACE_MS, 8003);
    expect(result.docker.state).toBe('unhealthy');
    expect(result.docker.detail).toMatch(/port 8003/);
    expect(result.docker.detail).toMatch(/Rebuild/);
    expect(result.since).toBe(10_000);
  });

  it('starts counting again once the container answers and later goes quiet', () => {
    const answered = judgeProbe({ state: 'running' }, 10_000, 90_000, 8003);
    expect(judgeProbe(silent, answered.since, 100_000, 8003).docker.state).toBe('starting');
  });
});
