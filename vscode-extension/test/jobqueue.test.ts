import { describe, expect, it } from 'vitest';
import { JobQueue, type Runner } from '../src/core/jobqueue';
import { parseStep } from '../src/core/progress';

describe('parseStep', () => {
  it('reads i/n from server messages', () => {
    expect(parseStep('Analysing video segment 3/8')).toEqual({ index: 3, total: 8 });
    expect(parseStep('File 1 / 2: a.txt')).toEqual({ index: 1, total: 2 });
    expect(parseStep('Consolidating')).toBeUndefined();
    expect(parseStep('9/2')).toBeUndefined();
  });
});

describe('JobQueue', () => {
  it('runs files one after another and records outcomes and progress', async () => {
    const order: string[] = [];
    const runner: Runner = async (file, _force, hooks) => {
      order.push(`start ${file}`);
      hooks.onStage('Analysing video segment 2/4');
      order.push(`end ${file}`);
      return { status: 'new' };
    };
    const snapshots: string[] = [];
    const queue = new JobQueue(runner, (jobs) => snapshots.push(jobs.map((j) => `${j.file}:${j.status}`).join(',')));

    await queue.enqueue(['a.txt', 'b.txt']);

    expect(order).toEqual(['start a.txt', 'end a.txt', 'start b.txt', 'end b.txt']);
    expect(queue.snapshot.map((j) => [j.file, j.status, j.outcome, j.step])).toEqual([
      ['a.txt', 'done', 'new', { index: 2, total: 4 }],
      ['b.txt', 'done', 'new', { index: 2, total: 4 }],
    ]);
    expect(snapshots.some((s) => s === 'a.txt:running,b.txt:queued')).toBe(true);
    expect(queue.busy).toBe(false);
  });

  it('reports errors from the server and from exceptions, and carries on', async () => {
    const runner: Runner = async (file) => {
      if (file === 'bad.pdf') {
        return { status: 'error', error: 'boom' };
      }
      if (file === 'throw.pdf') {
        throw new Error('network');
      }
      return { status: 'cached' };
    };
    const queue = new JobQueue(runner, () => undefined);
    await queue.enqueue(['bad.pdf', 'throw.pdf', 'ok.pdf']);
    expect(queue.snapshot.map((j) => [j.status, j.error])).toEqual([
      ['error', 'boom'],
      ['error', 'network'],
      ['done', undefined],
    ]);
  });

  it('cancel aborts the running file and drops the waiting ones', async () => {
    let release!: () => void;
    const started = new Promise<void>((resolve) => {
      release = resolve;
    });
    const runner: Runner = (file, _force, hooks) =>
      new Promise((_, reject) => {
        if (file === 'a.mp4') {
          release();
        }
        hooks.signal.addEventListener('abort', () => reject(new Error('aborted')));
      });
    const queue = new JobQueue(runner, () => undefined);
    const done = queue.enqueue(['a.mp4', 'b.mp4', 'c.mp4']);
    await started;

    queue.cancel();
    await done;

    expect(queue.snapshot.map((j) => j.status)).toEqual(['cancelled', 'cancelled', 'cancelled']);
    expect(queue.busy).toBe(false);
  });

  it('does not queue a file twice and starts a fresh batch after finishing', async () => {
    const seen: string[] = [];
    const queue = new JobQueue(async (file) => {
      seen.push(file);
      return { status: 'new' };
    }, () => undefined);
    const first = queue.enqueue(['a.txt']);
    const second = queue.enqueue(['a.txt', 'b.txt']);
    await Promise.all([first, second]);
    expect(seen).toEqual(['a.txt', 'b.txt']);
    await queue.enqueue(['a.txt'], true);
    expect(queue.snapshot.map((j) => j.file)).toEqual(['a.txt']);
  });
});
