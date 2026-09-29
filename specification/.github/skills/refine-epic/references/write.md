# Mode 1: Write a New Epic

1. Read the template, `.github/instructions/requirements.instructions.md`, the
   domain model `<paths.domain_model>`, `paths.requirements_index`,
   [content-rules.md](content-rules.md), and any source document the user
   references (`paths.requirement_sources`).
2. Determine the next epic number (highest existing + 1).
3. Ask for missing inputs: owner, priority (from `specification.priorities`),
   business context.
4. Create the file with every template section filled:
   - Header with the configured initial state (first value of
     `specification.states` unless evidence supports another).
   - Overview, feature index, dependencies, references.
   - For each feature: action-verb title, source, priority, state, owner,
     description, scenarios, comments, an empty Tasks table (filled later by
     `link-issues` or by hand), acceptance criteria, technical notes, testing
     notes, and the E2E section only when enabled.
   - Progress summary computed from actual states (see
     [checks.md](checks.md#progress-summary)).
   - Change history with the creation entry.
5. Regenerate the index (which adds the new epic to
   `paths.requirements_index`) and, when enabled, the consolidated document
   (see *Index and consolidation* in `../SKILL.md`).
6. Report the file path and a summary (features, scenarios) and ask for
   review.

**Output:** new file under `paths.epics` named per
`identifiers.epic.file_pattern`, plus the regenerated index and, when enabled,
the regenerated consolidated document.
