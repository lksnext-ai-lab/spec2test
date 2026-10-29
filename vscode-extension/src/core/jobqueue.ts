import type { Job, JobStatus } from '../shared/types';
import { parseStep } from './progress';

export type { Job, JobStatus };

export interface RunHooks {
  signal: AbortSignal;
  onStage(message: string): void;
}

export type Runner = (
  file: string,
  force: boolean,
  hooks: RunHooks,
) => Promise<{ status: string; error?: string }>;

/** Runs the files of a project one after the other, reporting every change. */
export class JobQueue {
  private jobs: Job[] = [];
  private controller?: AbortController;
  private running?: Promise<void>;

  constructor(
    private readonly runner: Runner,
    private readonly onChange: (jobs: readonly Job[]) => void,
  ) {}

  get snapshot(): readonly Job[] {
    return this.jobs;
  }

  get busy(): boolean {
    return this.running !== undefined;
  }

  /** Queue `files`; files already waiting or running are not queued twice. */
  enqueue(files: string[], force = false): Promise<void> {
    const active = new Set(this.jobs.filter((j) => j.status === 'queued' || j.status === 'running').map((j) => j.file));
    const fresh = files.filter((file) => !active.has(file));
    if (this.jobs.every((j) => j.status !== 'queued' && j.status !== 'running')) {
      this.jobs = [];
    }
    this.jobs.push(...fresh.map((file): Job => ({ file, force, status: 'queued' })));
    this.emit();
    this.running ??= this.drain();
    return this.running;
  }

  /** Abort the running file and drop everything still waiting. */
  cancel(): void {
    for (const job of this.jobs) {
      if (job.status === 'queued') {
        job.status = 'cancelled';
      }
    }
    this.controller?.abort();
    this.emit();
  }

  private async drain(): Promise<void> {
    try {
      for (;;) {
        const job = this.jobs.find((j) => j.status === 'queued');
        if (!job) {
          return;
        }
        await this.run(job);
      }
    } finally {
      this.running = undefined;
      this.emit();
    }
  }

  private async run(job: Job): Promise<void> {
    this.controller = new AbortController();
    const { signal } = this.controller;
    job.status = 'running';
    this.emit();
    try {
      const result = await this.runner(job.file, job.force, {
        signal,
        onStage: (message) => {
          job.stage = message;
          job.step = parseStep(message) ?? job.step;
          this.emit();
        },
      });
      job.outcome = result.status;
      if (signal.aborted) {
        job.status = 'cancelled';
      } else if (result.status === 'error') {
        job.status = 'error';
        job.error = result.error;
      } else {
        job.status = 'done';
      }
    } catch (error) {
      if (signal.aborted) {
        job.status = 'cancelled';
      } else {
        job.status = 'error';
        job.error = error instanceof Error ? error.message : String(error);
      }
    } finally {
      this.controller = undefined;
      this.emit();
    }
  }

  private emit(): void {
    this.onChange(this.jobs.map((job) => ({ ...job })));
  }
}
