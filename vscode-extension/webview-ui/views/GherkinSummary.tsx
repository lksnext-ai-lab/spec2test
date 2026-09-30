import type { AppState } from '../../src/shared/messages';
import { Icon } from '../ui/Icon';
import { send } from '../vscode';

/** Above the file list while the Gherkin view is on: totals, and the entries that need attention. */
export function GherkinSummary({ state }: { state: AppState }) {
  const { gherkin } = state;
  const unknown = gherkin.warnings.filter((warning) => warning.kind === 'unknown-source');
  const untraced = gherkin.warnings.filter((warning) => warning.kind === 'untraced');

  if (gherkin.error) {
    return (
      <div className="callout warn" role="alert">
        {gherkin.error}
      </div>
    );
  }
  return (
    <div className="gherkin-summary">
      <div className="muted small">
        {gherkin.features} feature{gherkin.features === 1 ? '' : 's'} · {gherkin.scenarios} scenario{gherkin.scenarios === 1 ? '' : 's'}
        {gherkin.folder ? ` in ${gherkin.folder.split(/[\\/]/).filter(Boolean).slice(-2).join('/')}` : ''}
      </div>
      {gherkin.warnings.length > 0 ? (
        <details className="gherkin-warnings">
          <summary>
            <Icon name="alert" size={14} />
            {unknown.length > 0 ? `${unknown.length} unknown input${unknown.length === 1 ? '' : 's'}` : ''}
            {unknown.length > 0 && untraced.length > 0 ? ' · ' : ''}
            {untraced.length > 0 ? `${untraced.length} scenario${untraced.length === 1 ? '' : 's'} without a source` : ''}
          </summary>
          <ul>
            {gherkin.warnings.map((warning) => (
              <li key={`${warning.file}:${warning.line}:${warning.text}`}>
                <button className="link" onClick={() => send({ type: 'openScenario', file: warning.file, line: warning.line })}>
                  {warning.text}
                </button>
                <span className="gherkin-path">
                  {warning.file}:{warning.line}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}
