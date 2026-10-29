# Harness Reference

This reference gathers the template's technical operation: requirements, traceability, CBM, agents, skills, scripts, templates, and validation.

## Requirements model

Define at least business objective, scope, actors, preconditions, main flow, exceptions, result, business rules, acceptance criteria, dependencies, priority, status, owner, and source. Confirm whether scenarios use tables, Gherkin, or both.

Criteria must be observable, verifiable, cover expected behavior and relevant errors, and link to a test. Recommended format:

```text
- [ ] Given [precondition], when [action], then [result]
```

Do not mix requirement status, implementation status, and test result.

### Configured values

States, task states, verification states, priorities, and size options are always
the literal values configured in `.project.yml` (`specification.states`,
`specification.task_states`, `specification.verification_states`,
`specification.priorities`, and `github_projects.fields.Size.options`). Do not translate,
abbreviate, or add aliases. For `en` installations the installer writes these
English defaults:

- States: `Pending`, `In analysis`, `Approved`, `In development`, `In testing`,
  `Completed`, `Blocked`, `Rejected`.
- Task states: `Open`, `Closed`, `No issue`.
- Verification states: `Not defined`, `Declared`, `In implementation`,
  `Implemented`, `Not applicable`.
- Priorities: `Critical`, `High`, `Medium`, `Low`, `Future`.
- Size options: `Small`, `Medium`, `Large`.

If a project changes these values in `.project.yml`, epics, plans, and the
traceability matrix must use the new literals.

## Sources, decisions, and traceability

Record each source with identifier, document name, location, date, author, section or page, and related requirement. Decisions should preserve the problem, source, proposed destination, impact, decision, rationale, owner, and date.

Preserve this relationship, adapting it to the project:

```text
Source -> Requirement -> Epic -> Feature -> Scenario -> Task -> PR -> Test
```

Generated documents must not replace their source files.

Requirements enter through two paths, both started with `analyst-requirements`:

```text
Documents: RSRC-N (requirement-sources) -> REQ-N (decisions, decide-requirement) -> refine-epic -> epic -> matrix
Code:      audit (audit-domain) -> validation -> create-domain-model ---------------> refine-epic -> epic -> matrix
```

Findings from code go from the audit to the epic once the user confirms them,
always through `create-domain-model`, which creates or updates the domain model
`<paths.domain_model>` and the glossary `<paths.glossary>` first. They are not
registered as `RSRC-N` or `REQ-N`, and `decisions.md` only records decisions on
documentary sources.

The **Source** of features and scenarios accepts several types, each as a
verifiable link and separated by `;` when there are several: document
(document + section), code (alias + symbol), test (alias + test path + case),
contract (alias + specification file + operation), data (alias + migration or
entity), and history (`alias#N` of a pull request or issue). No source, alone or
combined, establishes the completed state without human validation.

In the traceability matrix, a scenario discovered in code cites the audit ID
(for example `audit-orders-2026-09-27`) as requirement source. Behavior that
already existed before the kit and never had an issue keeps the configured
no-issue task state, even when the scenario is completed in the epic after
human validation, with the note `Already implemented; validated by @user on
DD/MM/YYYY`.

## E2E and retrospective audit

Configure the test repository, framework, feature location, tags, steps, page objects or fixtures, command, statuses, and evidence. Keep separate: whether functionality is implemented and whether an automated test exists and has a result.

In an audit distinguish observed capability, implementation linked to an issue or execution, and verification with an identifiable result. An observed capability does not prove a completed scenario or E2E coverage. Record missing features, steps, or results as evidence limitations. Before regenerating indexes, check real sections, duplicate IDs, and unexplained gaps.

The `audit-domain` skill starts with the entry-point inventory and then answers
seven fixed questions, each with the best available tool: which behaviors the
tests pin down, which capabilities are exposed (specification files, routes),
which entities, states, and rules exist, who can do what, how the user names
things (vocabulary for the glossary), why it exists (commits, pull requests,
issues), and what calls what. A question without application or tool is marked
not applicable or not available with the reason. Each finding carries a
verifiable link and a confidence level (high, medium, low) that stays in the
audit. Contradictions between sources are listed as questions for the owner and
copied as open questions to the scenario comments; nobody resolves them alone.

## Evidence with codebase-memory-mcp

When `integrations.codebase_memory.enabled` is active and an audit is explicitly
authorized, use `codebase-memory-mcp` to inspect architecture, modules, symbols,
and calls. Install it outside the destination only with explicit consent,
restrict `CBM_ALLOWED_ROOT` to the approved implementation root, review
`.cbmignore` before indexing (the installed `.gitignore` already covers
`.codebase-memory/` and `.vscode/mcp.json`), and locate its cache with
`CBM_CACHE_DIR` outside the repository. Configuration,
each indexing operation, and auditing have separate approval boundaries.

Install the version pinned in `integrations.codebase_memory.version` of
`.project.yml` outside the destination. The template's current value is
`v0.11.0`; the pip specifier omits the leading `v`:

```console
python -m pip install --upgrade "codebase-memory-mcp==0.11.0"
codebase-memory-mcp --version
```

Here `python` must be the verified active interpreter; if the terminal resolves
another one, invoke the verified interpreter by its executable path.

Resolve and verify the active Python interpreter before and after installation;
do not rely on a package manager's success message alone. Restart VS Code when
the MCP client configuration changes and verify the entry point from the same
interpreter. Do not copy the binary, `node_modules`, cache, or indexes to the
destination.

Register the MCP server as `codebase-memory-mcp`: agents reference its tools as
`codebase-memory-mcp/<tool>`. `operator-codebase-memory` declares the index tools
and `analyst-requirements` the read-only query tools, both limited to
`integrations.codebase_memory.allowed_tools`.

CBM is optional and one tool among others; without it only the structural
questions of the audit degrade. Responsibilities are separate:

```text
analyst-requirements
   |-(optional)-> operator-codebase-memory -> index ready and coverage, or "CBM not available"
   |------------> audit-domain            -> findings with evidence, confidence, and contradictions
   |------------> human validation        -> approved / defect / open question
   |------------> create-domain-model     -> domain model and glossary (mandatory)
   '------------> refine-epic             -> requirements in epics
```

The operator only installs, indexes, and reports freshness and coverage; it
never inventories or audits. After the validated audit the flow always
continues with `create-domain-model` and then `refine-epic`; `analyze-impact`
and `analyze-requirement` come later, when implementation is planned.

Each audit records alias, project, commit or generation, query, symbol or path, coverage, confirmation, and limitations. CBM demonstrates observed structure, not business value, functional compliance, or test results. Without CBM, use local search and state the reduced scope.

## Agents, skills, and scripts

`analyst-requirements` is the single entry point for requirements work and the only agent that edits epics, the domain model, the glossary, and the traceability matrix. It invokes `analyst-source-traceability` (documentary sources and decisions), `analyst-issue-traceability` (GitHub issues), `analyst-e2e-traceability` (E2E, when enabled), and optionally `operator-codebase-memory` (CBM index) as subagents; they return results or proposals and never hand the work back. They remain user-invocable and, when called directly, end by offering the handoff to `analyst-requirements`. `analyst-quality-auditor` audits the kit configuration and is invoked only by the user.

The catalogue below places each agent and skill in the workflow configured in
`workflow.stages`, using its identifiers literally:

```text
specify -> analyze -> plan -> approve -> create_tasks -> implement -> test -> trace
```

`approve` is a human step: the approvals configured in `workflow`
(`approval_required_before_issues`, `approval_required_before_implementation`)
are satisfied by the user, not by an agent.

### Agents

| Agent | Stage | Responsibility |
|-------|-------|----------------|
| `analyst-requirements` | `specify`, `analyze`, `trace` | Single entry point; edits epics, domain model, glossary, and matrix; produces the task breakdown and hands off to `orchestrator-implementation`. |
| `analyst-source-traceability` | `specify` | Compares documentary sources with epics and records each `REQ-N` decision with `decide-requirement`. |
| `operator-codebase-memory` | `specify` (optional) | Installs, configures, and indexes CBM and reports freshness and coverage; never audits. |
| `orchestrator-implementation` | `plan`, `approve`, `implement` | Consolidates the approved analysis and breakdown into an implementation plan with the specialists declared in `repositories[].specialist_agent`, gets it approved, hands off to `product-owner` to create tasks, then implements; does not write application code itself. |
| `product-owner` | `create_tasks` | After the implementation plan is approved, creates task issues and the epic-level issue and sets GitHub Projects fields. |
| `git-workflow` | `implement` | Branches, commits, and pull requests for the configured repositories, with confirmation for every irreversible operation. |
| `analyst-issue-traceability` | `trace` | Matches GitHub issues to scenarios and proposes Tasks rows and implementation states. |
| `analyst-e2e-traceability` | `test`, `trace` | Links scenarios to E2E features, steps, and recorded results when E2E is enabled; read-only. |
| `analyst-quality-auditor` | any (user only) | Audits the kit configuration against this guide set and the active instructions. |

### Skills

| Skill | Used by | Stage | Result |
|-------|---------|-------|--------|
| `decide-requirement` | `analyst-source-traceability` | `specify` | Decision on each documentary requirement in `decisions.md`. |
| `audit-domain` | `analyst-requirements` | `specify` | Code audit with evidence, confidence, and contradictions. |
| `create-domain-model` | `analyst-requirements` | `specify` | Domain model and glossary from a validated audit. |
| `reconcile-requirements` | `analyst-requirements` | `specify` | After any epic change: reconcile domain model, glossary, and matrix, regenerate the index (and the consolidated document when enabled), and validate. |
| `refine-epic` | `analyst-requirements` | `specify` | Written, reviewed, or improved epics. |
| `analyze-impact` | `analyst-requirements` | `analyze` | Impact section (New, Modify, Reuse and risks) of `<paths.tasks>/<FEAT-id>/analysis-<FEAT-id>.md`. |
| `analyze-requirement` | `analyst-requirements` | `analyze` | Dependency-ordered task breakdown per repository alias in the same analysis document. |
| `plan-implementation` | `orchestrator-implementation` | `plan` | `<paths.tasks>/<FEAT-id>/implementation-plan.md` from the plan template, ready for human approval. |
| `create-task` | `product-owner` | `create_tasks` | Task issue for one configured repository alias, linked to the epic. |
| `manage-epic` | `product-owner` | `create_tasks` | Epic-level issue that groups the task issues of one epic. |
| `configure-project` | `product-owner` | `create_tasks` | GitHub Projects fields of the created issues. |
| `link-issues` | `analyst-issue-traceability` | `trace` | Proposed Tasks rows and scenario implementation states. |
| `link-e2e` | `analyst-e2e-traceability` | `test`, `trace` | Proposed changes to the E2E section of epics. |
| `run-analyst-workflow` | `analyst-requirements` | any | Analyst branch, pre-commit checks, tagged commits, and pull requests for requirement documents. |

Instructions under `.github/instructions/` are injected automatically by their
`applyTo`; `project-workflow.instructions.md` keeps only the always-needed core.
The detailed rules live in `.github/instructions/references/` and are read on
demand: `workflow-rules.md` (evidence, requirement documents, change control,
repository roles, code evidence) and `change-history.md` (Author and Agent
attribution for every history row).

### Scripts

Scripts are run from the repository root with `python`:

| Script | Purpose |
|--------|---------|
| `scripts/idx.py` | `build [--check]` regenerates the epic index after editing epics (`--check` only verifies it); `stats` and `find <ID>` query it; `version [--kit <path>]` shows installed metadata and optionally compares commits with a local kit checkout. |
| `scripts/consolidate-epics.py` | Generates the consolidated epics document (`--check` only verifies it); runs only when `modules.consolidate_epics` and `features.consolidate_epics.enabled` are `true`. |
| `scripts/project_config.py` | Shared `.project.yml` reader used by the other scripts. |
| `.github/skills/configure-project/scripts/set-project-fields.py` | Default route to set GitHub Projects fields. |

Agents, skills, and scripts read project names, paths, repositories,
technology, commands, roles, approvals, and links from `.project.yml`; change
them there instead of editing the files.

Do not commit caches, `__pycache__`, secrets, or absolute paths. The installed
`.gitignore` already excludes the usual local artifacts; the generated
`paths.requirements_index` and `epics-consolidated.md` stay versioned.

## Portable automation

Project-owned automation must not create, copy, invoke, or depend on PowerShell
files (`*.ps1`, `*.psm1`, `*.psd1`, or `*.ps1xml`). Use Python or an existing
cross-platform toolchain. The default route for GitHub Projects fields is
`.github/skills/configure-project/scripts/set-project-fields.py`; `product-owner`
declares no GitHub Projects MCP tools because their names change between
server versions. Add them to its `tools:` only if the destination needs them.

## Template contract

Every installation must include, under the requirements root
(`<requirements.local_root>/<paths.requirements>`, shown with the default
`paths.*` names):

```text
requirements/
├── templates/
│   ├── template-epic.md
│   ├── template-decision.md
│   ├── template-domain-model.md
│   ├── template-implementation-plan.md
│   ├── template-glossary.md
│   └── template-requirement-source.md
├── domain-model.md
├── domain-model/
│   └── glossary.md
├── decisions/decisions.md
├── requirement-sources/requirement-sources.md
├── epics/index.md
├── sources/
└── traceability-matrix.md
```

Outside the requirements root it must include the `<paths.tasks>/` directory
(each feature gets its own `<FEAT-id>/implementation-plan.md`, created from
the plan template when planning, not seeded by the installer), the empty
`<paths.plans>/` directory (temporary analysis plans from `decide-requirement`),
and `.github/pull_request_template.md`. The Pull Request template is
independent; the installer copies the one for the selected locale.

The installer also ensures the root `.gitignore` and `.gitattributes` (the
validator does not require them). In `new` mode it creates them; in
`integrate` mode it only appends the missing rules under an
`# Added by ProjectTraceKit` header and never removes or reorders your lines.
The `.gitignore` ignores `__pycache__/`, `*.py[cod]`, `.vscode/mcp.json`,
`.vscode/mcp.local.json`, `.codebase-memory/`, `**/glossary.md.bak`, and
`*.tmp`, and keeps `epics-consolidated.md` versioned; `.gitattributes`
enforces LF line endings.

## Validation and Checklist

The validator is not installed in destinations. From a ProjectTraceKit checkout,
validate a prepared destination with:

```console
python scripts/validate-template.py --root <destination-path> --requirements
```

Run `git diff --check` from the destination repository when reviewing its changes.

Before starting operational work, confirm the name, paths, aliases, board, IDs, statuses, glossary, sources, approvals, commands, agents, skills, examples, caches, secrets, links, and a complete sample epic. Do not replace configured pending markers with invented values; classify remaining markers as blocking, optional, or belonging to disabled modules.
