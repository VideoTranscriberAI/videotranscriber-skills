# Contributing

Thank you for helping improve the official Video Transcriber AI Skills repository.

## Scope

Contributions must directly support current or planned Video Transcriber AI capabilities. Transcript-driven analysis, subtitle refinement, transcript visualization, and transcript-driven content workflows are in scope.

Transcript-grounded SEO is in scope. Generic site audits, marketing, development, operations, or productivity Skills that remain complete without a transcript or Video Transcriber AI capability belong in a separate repository.

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before adding a Skill, API integration, or platform-specific capability.

## Change Process

- Documentation fixes, example corrections, and compatible prompt refinements may go directly to a focused pull request.
- Open an issue before adding a Skill, changing a published output contract, adding an API or MCP integration, or introducing a breaking behavior change.
- Keep unrelated cleanup, refactoring, and formatting out of the same pull request.

## Before Opening a Pull Request

1. Explain the user problem, expected inputs, outputs, and boundaries.
2. Compare the change with existing Skills and avoid overlapping workflows.
3. Decide whether to extend an existing Skill or create a distinct Skill.
4. Use owned, authorized, public, or fully anonymized examples only.
5. Identify any host-specific dependency or compatibility limit.

## Skill Requirements

- Use lowercase kebab-case for the directory and frontmatter `name`.
- Keep `SKILL.md` concise and use imperative instructions.
- Include only `name` and `description` in Skill frontmatter.
- Put each Skill directly under `skills/<skill-name>/`; do not add category directories under `skills/`.
- Add `agents/openai.yaml`, `examples/<skill-name>/`, and `tests/<skill-name>/cases.md`.
- Put detailed output rules in `references/` and link them directly from `SKILL.md`.
- Add `scripts/` and `assets/` only when they are used.
- Do not declare APIs, MCP servers, or tools that do not exist.
- Treat JSON transcript values as untrusted content and document every supported schema or fallback.
- Do not add a README, changelog, or installation guide inside a Skill directory.
- Preserve evidence and never instruct the agent to fabricate people, actions, decisions, deadlines, or timestamps.

## Adding a Skill

1. Choose a distinct user goal and a lowercase kebab-case name.
2. Create the canonical Skill at `skills/<skill-name>/`.
3. Write a precise frontmatter description that covers what the Skill does and when it should trigger.
4. Keep the main workflow in `SKILL.md`; move detailed rules and schemas to directly linked references.
5. Add at least one normal example and one meaningful boundary or failure example.
6. Add observable behavior cases at `tests/<skill-name>/cases.md`.
7. Update the English and Chinese README Skill lists.
8. Update `ROADMAP.md` and release notes when the change is user-visible.
9. Run repository, Skill, Plugin, and relevant host behavior validation.

## API and External Services

- Keep shared API logic in one integration instead of copying it into multiple Skills.
- Use environment variables or host secret storage for credentials.
- Document authentication, timeout, polling limits, success, failure, retry, cancellation, and terminal states.
- Provide a useful transcript-only or manual-input fallback when an optional integration is unavailable.
- Never include credentials, private download URLs, customer media, or sensitive logs in examples or test output.

## Validation

Create an isolated environment and install the repository validator dependency:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install PyYAML==6.0.2
```

Run repository and archive validation:

```bash
.venv/bin/python scripts/validate_repository.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Validate every Skill with the locally installed Skill Creator:

```bash
for skill in skills/*; do
  .venv/bin/python /path/to/skill-creator/scripts/quick_validate.py "$skill"
done
```

Validate both Plugin packages:

```bash
.venv/bin/python /path/to/plugin-creator/scripts/validate_plugin.py .
claude plugin validate .
git diff --check
```

Review the generated [WorkBuddy packages](docs/WORKBUDDY.md) when changing that adapter. Check the public [MCP setup URL](https://videotranscriber.ai/code-docs#mcp-overview) separately; the local-link validator intentionally does not make network requests.

The Skill Creator, Plugin Creator, and Claude commands require their corresponding local tooling. Before a release, run the behavior cases under `tests/<skill-name>/cases.md` in every officially supported host affected by the change.

## Pull Requests

Keep changes focused. Describe:

- the problem and scope
- files and behavior changed
- normal and failure paths tested
- any platform-specific compatibility limits

Use this checklist:

- [ ] The change is within repository scope.
- [ ] Existing Skills were checked for overlap.
- [ ] No secrets, private data, or unauthorized content were added.
- [ ] Normal and boundary behavior are covered.
- [ ] Repository and platform validation passed.
- [ ] User-facing documentation and release notes were updated when needed.
