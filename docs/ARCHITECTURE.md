# Repository Architecture

## Purpose

This repository contains the public, official Agent Skills for Video Transcriber AI. Its Skills should help users work with transcripts, subtitles, media transcription, and transcript-grounded downstream workflows.

Internal engineering, operations, or growth workflows that do not depend on Video Transcriber AI capabilities belong in a separate repository.

## Design Principles

1. Maintain one canonical Skill implementation under `skills/<skill-name>/`.
2. Keep Codex and Claude manifests thin. They expose the canonical Skills and must not duplicate Skill instructions.
3. Prefer extending an existing Skill when the user intent and output contract remain the same.
4. Create a new Skill when it has a distinct user goal, trigger, input boundary, or output contract.
5. Keep Skills portable. Platform-specific behavior must be optional and documented.
6. Keep examples public, authorized, or fully anonymized.
7. Preserve source evidence and do not fabricate facts, people, decisions, deadlines, metrics, or timestamps.

## Repository Layout

```text
videotranscriber-skills/
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── agents/
│       │   └── openai.yaml
│       ├── references/       # Optional detailed rules or schemas
│       ├── scripts/          # Optional deterministic helpers
│       └── assets/           # Optional output assets
├── examples/
│   └── <skill-name>/
├── tests/
│   └── <skill-name>/
│       └── cases.md
├── docs/
│   └── ARCHITECTURE.md
├── scripts/
│   └── validate_repository.py
├── integrations/workbuddy/   # Token connector metadata and credential form
├── .agents/                  # Codex marketplace manifest
├── .codex-plugin/            # Codex Plugin manifest
└── .claude-plugin/           # Claude Plugin and marketplace manifests
```

Each directory directly under `skills/` is one discoverable Skill. Do not add category directories such as `skills/seo/transcript-seo/`; use clear names such as `transcript-seo` instead.

## Canonical Skill and Thin Manifests

The canonical instructions, references, scripts, and assets live in `skills/<skill-name>/`. Codex and Claude manifests expose the repository and provide platform metadata only.

When behavior changes:

1. Update the canonical Skill.
2. Update its examples and behavior cases.
3. Update platform metadata only when discovery, branding, permissions, or packaged capabilities change.

Do not maintain separate Codex and Claude copies of the same `SKILL.md`.

## Skill Boundaries

Extend an existing Skill when:

- the user is pursuing the same primary goal;
- the new input feeds the same workflow;
- the output contract remains compatible; and
- adding the behavior does not make triggering ambiguous.

Create a new Skill when:

- the user intent is independently useful;
- the Skill needs a distinct trigger or safety boundary;
- the inputs or outputs differ materially; or
- the workflow would otherwise make an existing Skill broad and unpredictable.

Before adding a Skill, compare it with every existing Skill and document why extension or composition is insufficient.

## Naming

- Use lowercase kebab-case.
- Prefer a short action or domain phrase.
- Use consistent prefixes when they clarify related capabilities:
  - `transcript-*`
  - `subtitle-*`
  - `video-*`
- Keep the directory name and Skill frontmatter `name` identical.

## Minimum Skill Package

Every Skill must include:

```text
skills/<skill-name>/SKILL.md
skills/<skill-name>/agents/openai.yaml
examples/<skill-name>/
tests/<skill-name>/cases.md
```

Add `references/`, `scripts/`, or `assets/` only when the Skill actually needs them. Do not add README, changelog, or installation files inside an individual Skill directory.

Examples must include at least one normal path and one meaningful boundary or failure path. Tests should describe observable behavior rather than require identical prose.

## MCP Integration

Treat a Skill as the workflow and an API client, MCP server, or host tool as the capability.

The Video Transcriber AI workflow starts with `setup-videotranscriber` when a connection is missing. The business flow is:

```text
Media or URL
    ↓
transcribe-media + Video Transcriber AI MCP
    ↓
Transcript
    ↓
transcript-insights when analysis is requested
```

Rules:

- Keep transcription tool usage in `transcribe-media` rather than copying it into analysis Skills.
- Pass the resulting transcript into existing analysis workflows.
- Keep transcript-only usage available when the MCP connection is absent.
- Store credentials in the chosen client’s user configuration with restricted permissions or its native credential store, never in Skill/repository files. Environment variables are an explicit advanced option.
- Define success, failure, timeout, retry, cancellation, polling limits, and terminal-state handling.
- Do not claim an API, MCP server, or tool exists until its implementation and packaging are present.

The MCP connection is configured by the host client. The setup Skill uses one local private-input and discovery implementation with client-specific configuration adapters. It covers Codex, Claude Code, WorkBuddy, Cursor, Windsurf/Cascade, Gemini CLI, GitHub Copilot CLI, VS Code, Cline, and Roo Code. JSONC/TOML edits preserve unrelated settings, and ambiguous user profiles require selecting the active file before input. Discovery uses an explicit client User-Agent and distinguishes recognized API authentication errors from gateway rejections. The public Skills and packages contain no user's API Key.

The Codex manifest exposes the canonical Skills; setup guides the client-owned connection and credential. The Claude manifest supplies its own sensitive credential field and MCP mapping. WorkBuddy metadata lives under `integrations/workbuddy/`; the builder reads canonical Skills to create upload or connector archives without maintaining duplicate implementations.

Connection onboarding, an existing healthy connection, a revoked Key, transcript-only use, video-to-notes handoff, and task resumption are separate behavior cases. Validate public connection-documentation URLs as well as local links before release. Package validation does not substitute for target-client credential UI and restart testing.

## SEO Scope

Transcript-grounded SEO belongs in this repository. A future `transcript-seo` Skill may generate:

- video titles and descriptions;
- timestamped chapters;
- transcript-grounded keywords and FAQs;
- article or content briefs; and
- metadata derived from the source transcript.

It must not invent search volume, ranking, traffic, competition, or other external metrics without an authorized data source.

Generic site audits, Core Web Vitals, sitemap checks, Search Console analysis, competitor research, and internal marketing automation belong in a separate growth-oriented repository unless they become an explicit Video Transcriber AI product capability.

## Compatibility

Codex and Claude Code have dedicated plugin manifests; WorkBuddy has canonical Skill ZIPs and a Token connector adapter. Other supported local clients use standard Skills plus configuration adapters. Adapter tests verify formats and file handling; client-level discovery, input, and reload behavior is accepted separately using [CLIENT_TESTING](CLIENT_TESTING.md).

Platform-specific features must:

- be optional when possible;
- declare their dependency clearly;
- provide a useful fallback; and
- avoid changing the canonical behavior silently.

## Validation

Repository validation automatically discovers every direct child of `skills/`. Each Skill must pass:

- repository structure and local-link validation;
- Skill frontmatter validation;
- Codex Plugin validation;
- Claude Plugin validation; and
- relevant behavior cases in supported hosts.

Run the commands documented in `CONTRIBUTING.md` before release.

## Versioning and Releases

- Use semantic versions for the Plugin package.
- Patch releases fix documentation, prompts, validation, or behavior without breaking the contract.
- Minor releases add backward-compatible Skills, outputs, or integrations.
- Major releases may rename, remove, or materially change published contracts.
- Record user-visible changes in release notes.
- Do not tag or publish a release until the target commit is merged and validated.

## Documentation Responsibilities

- `README.md` and `README_zh.md`: product overview, installation, usage, and available Skills.
- `docs/ARCHITECTURE.md`: repository boundaries and long-term structure.
- `CONTRIBUTING.md`: concrete contribution and validation steps.
- `ROADMAP.md`: available, planned, and candidate capabilities.
- `RELEASE_NOTES.md`: release-specific user-visible changes.
