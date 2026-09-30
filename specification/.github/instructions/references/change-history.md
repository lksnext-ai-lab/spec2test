# Change History Attribution

This file is the single definition of the change-history attribution rule.
Agents, skills, and instruction files reference it instead of repeating it.
It is not auto-injected: read it before writing any change-history row or
other author attribution.

## Author

For any document history or other author attribution, use the authenticated
GitHub account login by default, unless the user explicitly specifies a
different author. Obtain the login with `gh api user --jq .login` in the
operational workspace; use only a nonempty, verified result. This identifies
the authenticated account, not necessarily the person who made every change.
Never infer the author from `git config user.name`, the operating-system user,
the repository owner, or previous history rows, and never expose credentials.
If GitHub CLI is unavailable, authentication fails, or no login is returned,
ask the user for the author before editing. If no verified login or explicit,
nonempty author is available, stop without writing the change. Never write a
history row with a missing, placeholder, or unregistered author, and never use
`GitHub Copilot` or an agent name as the author.

## Agent

- Record the agent name and the full visible model name, including its visible
  variant when available, for example `<agent-name> (<model and variant>)`. Do
  not reduce the model to its base family and do not use `GitHub Copilot` as
  the model.
- If the platform exposes the reasoning level, append
  `; thinking effort: <value>`.
- If the change was made manually, use `-` in the agent column.
- If the model is unknown, use `Unregistered model`.
- If the model variant or reasoning level is not exposed, omit only that
  metadata.
- Never infer or invent author, model, variant, or reasoning metadata.
