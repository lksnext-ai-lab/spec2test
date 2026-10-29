import { useState } from 'react';
import type { GherkinFeatureRef } from '../../src/shared/types';
import { Icon } from '../ui/Icon';
import { send } from '../vscode';

const open = (file: string, line: number) => () => send({ type: 'openScenario', file, line });

/** Under an input card: the features that cite it and, per feature, the scenarios that do. */
export function GherkinList({ features }: { features: GherkinFeatureRef[] }) {
  const [collapsed, setCollapsed] = useState(false);
  const scenarios = features.reduce((sum, feature) => sum + feature.scenarios.length, 0);

  if (features.length === 0) {
    return (
      <div className="gherkin gherkin-empty">
        <Icon name="checklist" size={14} /> Not referenced by any scenario
      </div>
    );
  }
  return (
    <div className="gherkin">
      <button className="gherkin-toggle" aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}>
        <Icon name={collapsed ? 'chevron-down' : 'chevron-up'} size={12} />
        <Icon name="checklist" size={14} />
        {scenarios} scenario{scenarios === 1 ? '' : 's'} · {features.length} feature{features.length === 1 ? '' : 's'}
      </button>
      {collapsed ? null : (
        <ul className="gherkin-features">
          {features.map((feature) => (
            <li key={feature.file}>
              <button className="gherkin-feature" onClick={open(feature.file, feature.line)} title={`Open ${feature.file}`}>
                <Icon name="feature" size={14} className="gherkin-icon gherkin-icon-feature" />
                <span className="gherkin-feature-name">{feature.name}</span>
                <span className="gherkin-path">{feature.file}</span>
              </button>
              <ul className="gherkin-scenarios">
                {feature.scenarios.length === 0 ? <li className="gherkin-path">Listed in the file header only</li> : null}
                {feature.scenarios.map((scenario) => (
                  <li key={scenario.line}>
                    <button className="gherkin-scenario" onClick={open(feature.file, scenario.line)} title={`Open at line ${scenario.line}`}>
                      <Icon name="scenario" size={13} className="gherkin-icon" />
                      <span className="gherkin-scenario-name">{scenario.name}</span>
                      <span className="gherkin-line">:{scenario.line}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
