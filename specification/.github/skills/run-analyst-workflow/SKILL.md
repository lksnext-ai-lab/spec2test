---
name: run-analyst-workflow
description: Used by analyst-requirements to guide the analyst Git workflow for requirement documents - branch creation and synchronization, pre-commit quality checks, tagged commits, pull requests from the repository template, conflict resolution, and safe reverts - with confirmation before every state-changing command. Use when requirement documentation changes must be branched, validated, committed, or proposed in a pull request.
---

# Analyst Workflow

Manages the Git lifecycle for publishing requirement documents. Content edits
belong to `refine-epic`.

## Configuration

Read `.project.yml`:

| Value | Key |
|-------|-----|
| Base branch | `repository.default_branch` (or `requirements.repository.default_branch` when set and `requirements.mode` is `external_repository`) |
| Pull request target | `repository.pull_request_target` |
| Repository | `repository.organization` / `repository.name` (or `requirements.repository.*` when `requirements.mode` is `external_repository`) |
| Analyst branch prefix | `workflow.analyst_branch_prefix` |
| Commit and PR tag | `workflow.analyst_commit_tag` |
| Scripts, epics, and index | `scripts/idx.py`, `scripts/consolidate-epics.py`, `paths.epics`, `paths.requirements_index` |
| Epic consolidation | `modules.consolidate_epics`, `features.consolidate_epics.enabled` |

If a needed value is unresolved (see the unresolved-value rule in
`project-workflow.instructions.md`), stop and ask the user to configure it.
Never checkout, merge, or push with an unresolved value.

When `requirements.mode` is `external_repository`, the operational workspace
stays the main repository (see `requirements.instructions.md`); do not open
the requirements repository as a separate workspace. Run every Git command in
this skill against the requirements repository at
`requirements.repository.local_path` instead — for example with `git -C
<local_path> ...` or by changing directory to it first — because that path
holds its own working tree, branches, and remote. `paths.plans` and
`paths.tasks` changes are never affected by this: they always commit against
the main repository's own base branch.

## Safety rules

- Before any checkout or merge, run `git status --porcelain`. If the tree is
  dirty, stop and let the analyst choose: commit (Mode B), stash with explicit
  confirmation, or abort. Never discard changes.
- Ask for explicit confirmation before each checkout, merge, commit, and push.
  Show the exact command first.
- Never push automatically, including after resolving conflicts.
- Never commit directly to the base branch.
- Never rewrite published history without explicit confirmation and an
  explanation of the consequences.

## Mode A: Create or synchronize the branch

1. Resolve the analyst branch: `<analyst_branch_prefix><identifier>`, where the
   identifier is the analyst's personal name for the branch (for example
   `analyst/jdoe` with the English defaults). Ask for the identifier when
   unknown; never derive it from the Git user or the operating system.
2. Check for a dirty tree (see safety rules).
3. Fetch and check whether the branch exists locally or on the remote:

   ```console
   git fetch origin
   git branch --list <analyst-branch>
   git ls-remote --heads origin <analyst-branch>
   ```

4. After confirmation of the exact commands:
   - **The branch exists** (locally or on `origin`): check it out and
     integrate the base branch.

     ```console
     git checkout <analyst-branch>
     git merge origin/<base-branch>
     ```

   - **The branch does not exist**: say so, show the name that will be
     created, and create it from the up-to-date base branch. Never create it
     from another analyst's branch or from a dirty tree.

     ```console
     git checkout -b <analyst-branch> origin/<base-branch>
     ```

   `git checkout <analyst-branch>` creates a local tracking branch when only
   `origin/<analyst-branch>` exists. Do not push the new branch here; the first
   push happens in Mode B after its own confirmation.
5. On conflicts, go to Mode D.
6. Report `git status` and `git log --oneline -5`, whether the branch was
   created or reused, and how many base commits were integrated.

## Mode B: Validate and commit

1. Show `git status` and `git diff --stat`.
2. For each modified file under `paths.epics`, check:
   - IDs unique and matching the configured `identifiers.*.pattern`.
   - No empty required sections or unresolved placeholders.
   - States, priorities, and acceptance criteria use the configured values and
     `specification.acceptance_criteria_format`.
   - Sources cited for features and scenarios.
   - Change history has a row for the change.
   - File name follows `identifiers.epic.file_pattern`.
   Report problems and stop until they are fixed or the analyst explicitly
   decides to continue.
3. When epics changed, always check that the generated index is up to date
   without writing it:

   ```console
   python scripts/idx.py build --check
   ```

   When `modules.consolidate_epics` and `features.consolidate_epics.enabled`
   are also both `true`, check the consolidated document too:

   ```console
   python scripts/consolidate-epics.py --check
   ```

   Both commands resolve the paths from `.project.yml` and exit with a non-zero
   code when the file is missing or stale (`consolidate-epics.py` ignores only
   its date line). If a check fails, run that command without `--check` and
   include the regenerated file in the commit alongside the epic changes; never
   edit generated files by hand.
4. Ask for a short description and propose
   `<analyst_commit_tag> <description>`.
5. After confirmation of the file list and message:

   ```console
   git add -- <confirmed-files>
   git commit -m "<analyst_commit_tag> <description>"
   ```

6. Ask separately before pushing. The first push of a branch created in Mode A
   sets its upstream:

   ```console
   git push -u origin <analyst-branch>
   ```

   Later pushes use `git push origin <analyst-branch>`.

## Mode C: Create a pull request

1. Run Mode A (with its checks and confirmations).
2. Gather changes:

   ```console
   git log origin/<base-branch>..<analyst-branch> --oneline
   git diff --stat origin/<base-branch>...<analyst-branch>
   ```

3. Title: `<analyst_commit_tag> <summary of the change set>`, for example
   `[ANALYSIS] Add two features to EPIC-4` with the English defaults.
4. Body: read `.github/pull_request_template.md` from the destination
   repository and fill every section it defines, in its order. Put the epic,
   feature, and scenario IDs in its traceability section. Reference issues with
   `Refs #N`; never use closing keywords (`Closes`, `Fixes`, `Resolves`),
   because completion requires human validation.
5. Show title and body and ask for confirmation.
6. Create the pull request with `github/create_pull_request`: base
   `repository.pull_request_target`, compare the analyst branch. Report the
   link.

## Mode D: Resolve conflicts

1. List conflicted files with `git status`.
2. For each file, explain both sides and propose a resolution. Apply it only
   after confirmation. If a conflict affects IDs or epic structure created by
   someone else, recommend consulting the technical lead; never renumber IDs to
   resolve a conflict.
3. After confirmation:

   ```console
   git add -- <resolved-files>
   git commit -m "<analyst_commit_tag> Resolve conflicts with <base-branch>"
   ```

4. Do not push. Offer Mode B step 6 and wait for confirmation.

## Mode E: Revert a commit

- **Preferred for any commit:** `git revert <hash>` creates an inverse commit.
  Show the commit and ask for confirmation.
- **Unpushed commit, rewrite requested:** `git reset --soft HEAD~1` only after
  explaining that it removes the commit from the branch history while keeping
  the changes staged, confirming the commit was not pushed, and receiving
  explicit confirmation.
- **Pushed commit:** never rewrite by default. A force push requires explicit
  confirmation, an explanation of the impact on collaborators, and
  `--force-with-lease`.

## Output

| Mode | Output |
|------|--------|
| A | Sync result and integrated commit count |
| B | Validation report, commit hash, push result when confirmed |
| C | Pull request link |
| D | Resolved files and commit hash (not pushed) |
| E | Final repository state |
