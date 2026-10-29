import { useEffect, useRef, useState } from 'react';
import type { FileCard as File, GherkinFeatureRef, Job } from '../../src/shared/types';
import { Icon, type IconName } from '../ui/Icon';
import { formatSize, relativeTime } from '../util';
import { send } from '../vscode';
import { GherkinList } from './GherkinList';

type OpenKind = 'original' | 'cache' | 'cache-preview' | 'preprocessed' | 'images';

const KIND: Record<string, { icon: IconName; label: string; className: string }> = {
  '.pdf': { icon: 'file-text', label: 'PDF', className: 'kind-pdf' },
  '.mp4': { icon: 'video', label: 'MP4', className: 'kind-video' },
  '.md': { icon: 'file-text', label: 'MD', className: 'kind-md' },
  '.txt': { icon: 'file', label: 'TXT', className: 'kind-txt' },
};

function status(file: File, job?: Job): { text: string; kind: string } {
  if (job?.status === 'running') return { text: 'Processing', kind: 'running' };
  if (job?.status === 'queued') return { text: 'Queued', kind: 'queued' };
  if (job?.status === 'error') return { text: 'Failed', kind: 'error' };
  if (job?.status === 'cancelled') return { text: 'Cancelled', kind: 'queued' };
  return { cached: { text: 'Processed', kind: 'ok' }, new: { text: 'New', kind: 'warn' }, stale: { text: 'Changed', kind: 'warn' }, renamed: { text: 'Renamed', kind: 'warn' } }[file.state];
}

function IconButton(props: { icon: IconName; label: string; onClick: () => void; disabled?: boolean; danger?: boolean; badge?: number }) {
  return (
    <button className={`icon-btn ${props.danger ? 'danger' : ''}`} title={props.label} aria-label={props.label} disabled={props.disabled} onClick={props.onClick}>
      <Icon name={props.icon} />
      {props.badge ? <span className="icon-badge">{props.badge}</span> : null}
    </button>
  );
}

export function FileCard({ file, job, canProcess, gherkin, highlight }: { file: File; job?: Job; canProcess: boolean; gherkin?: GherkinFeatureRef[]; highlight?: number }) {
  const element = useRef<HTMLLIElement>(null);
  const [flash, setFlash] = useState(false);
  // A new highlight nonce scrolls this card into view and flashes it (used by links in .feature files).
  useEffect(() => {
    if (!highlight) {
      return undefined;
    }
    element.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    setFlash(true);
    const timer = setTimeout(() => setFlash(false), 1800);
    return () => clearTimeout(timer);
  }, [highlight]);

  const kind = KIND[file.format] ?? KIND['.txt'];
  const s = status(file, job);
  const active = job?.status === 'running' || job?.status === 'queued';
  const open = (what: OpenKind) => () => send({ type: 'open', file: file.name, kind: what });
  const hasPre = file.format === '.pdf' || file.format === '.md';
  const step = job?.step;

  return (
    <li ref={element} className={`file file-${s.kind} ${flash ? 'is-flash' : ''}`}>
      <div className={`file-icon ${kind.className}`} aria-hidden="true">
        <Icon name={kind.icon} size={18} />
        <span>{kind.label}</span>
      </div>
      <div className="file-main">
        <div className="file-head">
          <button className="file-name" title={`Open ${file.name}`} onClick={open('original')}>
            {file.name}
          </button>
          <span className={`status status-${s.kind}`}>
            <span className="status-dot" />
            {s.text}
          </span>
        </div>
        <div className="file-meta">
          {formatSize(file.size)}
          {file.processedAt ? ` · ${relativeTime(file.processedAt)}` : ''}
          {file.model ? ` · ${file.model}` : ''}
        </div>

        {job?.status === 'running' ? (
          <div className="file-progress" role="status">
            <span>{job.stage ?? 'Starting…'}</span>
            <div className={`bar ${step ? '' : 'indeterminate'}`}>{step ? <div className="fill" style={{ width: `${(step.index / step.total) * 100}%` }} /> : null}</div>
          </div>
        ) : null}
        {gherkin ? <GherkinList features={gherkin} /> : null}
        {job?.status === 'error' && job.error ? <p className="file-error">{job.error}</p> : null}

        <div className="file-actions">
          <div className="file-chips">
            <button className="chip-btn" onClick={open('original')} title="Open the original file">
              <Icon name="file" size={14} /> Original
            </button>
            {hasPre ? (
              <button className="chip-btn" onClick={open('preprocessed')} disabled={!file.hasPreprocessed} title={file.hasPreprocessed ? 'Open the pre-processed Markdown' : 'Available after processing'}>
                <Icon name="layers" size={14} /> Pre-processed
              </button>
            ) : null}
            <button className="chip-btn" onClick={open('cache')} disabled={!file.hasCache} title={file.hasCache ? 'Open the cached result' : 'Available after processing'}>
              <Icon name="file-text" size={14} /> Result
            </button>
          </div>
          <div className="file-tools">
            {file.hasCache ? <IconButton icon="eye" label="Preview the result" onClick={open('cache-preview')} /> : null}
            {file.hasImages ? <IconButton icon="image" label="Show extracted images" onClick={open('images')} /> : null}
            {file.history.length > 0 ? <IconButton icon="clock" label="Compare with earlier results" badge={file.history.length} onClick={() => send({ type: 'history', file: file.name })} /> : null}
            <IconButton
              icon={file.state === 'cached' ? 'refresh' : 'play'}
              label={file.state === 'cached' ? 'Reprocess' : 'Process'}
              disabled={active || !canProcess}
              onClick={() => send({ type: 'process', files: [file.name], force: file.state === 'cached' })}
            />
            <IconButton icon="trash" label="Remove from project" danger disabled={active} onClick={() => send({ type: 'removeFile', file: file.name })} />
          </div>
        </div>
      </div>
    </li>
  );
}
