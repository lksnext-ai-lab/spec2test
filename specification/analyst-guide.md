# Analyst Guide - Requirements Management

This guide provides step-by-step instructions for analysts documenting requirements with epics, features, and scenarios in Markdown.

## Introduction

This guide helps you document functional requirements clearly and traceably using Markdown and GitHub. Identity, paths, and formats are read from `.project.yml`.

## Index

- [Branch Strategy](#branch-strategy)
- [Initial Setup](#initial-setup)
- [Daily Workflow](#daily-workflow)
- [Pull Requests](#pull-requests)
- [Essential Git Commands](#essential-git-commands)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Branch Strategy

The branch prefix and the commit/Pull Request tag come from `.project.yml`:

- `workflow.analyst_branch_prefix`: branch prefix. When empty, the `en` default is `analyst/`.
- `workflow.analyst_commit_tag`: commit and Pull Request title tag. When empty, the `en` default is `[ANALYSIS]`.

The examples below use `<prefix>` for the resolved branch prefix, `<tag>` for the resolved tag, and
`<base>` for the configured base branch (`repository.default_branch`). Pull Requests target
`repository.pull_request_target`.

- **`<base>`**: Approved and official documentation version
- **`<prefix>[your-name]`** (for example `analyst/[your-name]`): Your personal work branch

**Important:** Each analyst works on their own branch and requests review before integrating changes into `<base>`.

---

## Initial Setup

```bash
git clone [repository-URL]
git checkout -b <prefix>[your-name]
git push -u origin <prefix>[your-name]
```

> Always use the configured `<prefix>your-name` format for your branch.

> Verify your current branch with `git branch` before starting work.

---

## Daily Workflow

### At the Start of the Day

**Always synchronize your branch with the latest approved version.**
This ensures that you work with the latest documentation and avoid conflicts.

```bash
# 1. Switch to the base branch and update it
git checkout <base>
git pull origin <base>

# 2. Return to your personal branch
git checkout <prefix>[your-name]

# 3. Bring the latest <base> changes into your branch
git merge <base>
```

---

### During Work

#### 1. Create or Edit Epics

Epic files are stored at the path configured in `paths.epics`:

- Ask `@analyst-requirements` to create or edit epics, features, and
  scenarios using the official template; it also incorporates documentary
  sources, code audits, and issue or E2E links for you.
- Cite each source as a verifiable link: document, code, test, contract, data,
  or history (pull request or issue); separate several with `;`.
- Answer the open questions that an audit leaves in the scenario comments; do
  not resolve a contradiction without the owner.
- Complete all required fields and verify the IDs.
- Before saving, check that:
  - All IDs are unique.
  - No required fields are missing.
  - Sources are cited correctly.
  - The change history is up to date.
  - You regenerated the index with `python scripts/idx.py build` (never edit
    it by hand).
  - When `modules.consolidate_epics` and `features.consolidate_epics.enabled`
    are `true`, you regenerated the consolidated document with
    `python scripts/consolidate-epics.py`.
- For your first pieces of work (sources, code, epics, issues, tasks, and
  publishing), follow the
  [First tasks](projecttrace-guide/UsageGuide.md#first-tasks) of the
  operational guide.

---

### At the End of Changes

```bash
# 1. See which files changed
git status

# 2. Stage only the files you intend to commit
git add [modified-files]

# 3. Commit with a descriptive message
git commit -m "<tag> Clear change description"

# 4. Push changes to GitHub
git push origin <prefix>[your-name]
```

---

## Pull Requests

### Step 1: Prepare Your Branch

Before creating a PR, make sure your branch is up to date:

```bash
# Synchronize with the base branch
git checkout <base>
git pull origin <base>
git checkout <prefix>your-name
git merge <base>

# Check that there are no conflicts
git status
```

### Step 2: Go to GitHub

1. Navigate to the repository on GitHub.
2. Select **Pull Requests** -> **New Pull Request**.
3. Select:
   - **Base:** the `repository.pull_request_target` branch
   - **Compare:** `<prefix>your-name`

### Step 3: Complete the Form

The repository provides a Pull Request template in `.github/pull_request_template.md`; complete every section it asks for.

**Title:**

```text
<tag> Brief description of the change
```

Examples with the `en` default tag:

- `[ANALYSIS] Updated scenarios and domain model`
- `[ANALYSIS] Added new features to an epic`

**Description:**

Fill in the sections of `.github/pull_request_template.md`. A short example for
a requirements change:

```markdown
## Summary

Updated the scenarios of a feature after the source review.

## Traceability

- Epic: EPIC-N
- Feature: FEAT-N-M
- Scenarios: ESC-N-M-K
- Issue: n/a
- Repository or alias: <alias from .project.yml>
- [ ] Human validation recorded before marking any requirement as completed

## Change Type

- [x] Requirement or documentation

## Validation

- [x] Manual validation completed where applicable
- [x] Documentation updated

## Risks and Dependencies

None.
```

### Step 4: Create the PR

Click **Create Pull Request** and wait for the team review.

### Step 5: Respond to Comments

If changes are requested:

```bash
# Make the changes in your branch
git add [modified-files]
git commit -m "<tag> Changes requested during review: [brief description]"
git push origin <prefix>your-name
```

The PR updates automatically.

### Step 6: Integration into the Base Branch

Once the PR has the required approval, a reviewer merges it following the
repository rules; do not merge your own Pull Request.

After the merge, update your local copy:

```bash
git checkout <base>
git pull origin <base>
```

---

## Essential Git Commands

### View Current Status

```bash
git status
# Shows modified, added, and other files
```

### View Change History

```bash
git log --oneline
# Shows recent commits in summary form
```

### View Differences

```bash
git diff
# Shows modified lines
```

### Discard Uncommitted Changes

```bash
git checkout -- .
# WARNING: This deletes uncommitted changes
```

### Undo the Last Commit Before Push

```bash
git reset --soft HEAD~1
# Undoes the last commit while keeping the changes
```

---

## Best Practices

### DO

- Make frequent, small commits.
- Use clear, descriptive messages.
- Synchronize your branch with `<base>` every day.
- Request review before merging.
- Always cite requirement sources.
- Use the official template.
- Keep the change history up to date.

### DO NOT

- Change existing IDs.
- Commit directly to `<base>`.
- Merge without review or merge your own Pull Request.
- Leave required fields empty.
- Invent IDs outside the hierarchy.
- Copy and paste without adapting to the context.

> Requirement quality and traceability depend on following these practices.

---

## Troubleshooting

### "I have conflicts in my PR"

1. Update your branch with the base branch:

   ```bash
   git checkout <prefix>your-name
   git fetch origin
   git merge origin/<base>
   ```

2. Review the conflicting files and resolve them manually.
3. Mark the resolved files:

   ```bash
   git add [resolved-files]
   git commit -m "<tag> Resolved conflicts with <base>"
   git push origin <prefix>your-name
   ```

> If you are unsure, ask your technical lead for help.

---

### "I made a mistake in my last commit"

- If you have NOT pushed:

  ```bash
  git reset --soft HEAD~1
  # Correct the changes and commit again
  ```

- If you HAVE pushed:
  > Talk to your technical lead before making changes.

---

Part of ProjectTraceKit. The installed version is recorded in `template.version`
of `.project.yml`; see the ProjectTraceKit `CHANGELOG.md` for its changes.
