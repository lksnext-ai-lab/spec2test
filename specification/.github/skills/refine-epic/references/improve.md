# Mode 3: Improve an Existing Epic

1. Read the same references as Mode 2 ([review.md](review.md)) plus
   [content-rules.md](content-rules.md), and run the checks when no review
   exists.
2. Propose every change and apply it only after the user confirms. Mechanical
   fixes (missing columns, outdated feature index, progress summary recount,
   missing change history section) may be grouped into one confirmation.
3. ID changes (duplicates, renumbering) require a separate, explicit
   confirmation that lists every affected ID and its references.
4. Content additions (acceptance criteria, notes, Gherkin rewrites, new
   features or scenarios) are proposed individually and applied after
   confirmation.
5. Never fill the Tasks table by guessing: offer `link-issues`, or manual rows
   the user supplies.
6. Update the header's last-updated date and the change history.
7. Regenerate the index and, when enabled, the consolidated document (see
   *Index and consolidation* in `../SKILL.md`).
8. Report applied changes, pending items, and the resulting state.

**Output:** epic modified in place after confirmation, plus the regenerated
index and, when enabled, the regenerated consolidated document. See
[examples.md](examples.md) for a worked review followed by an improvement.
