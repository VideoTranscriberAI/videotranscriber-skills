# Release Notes

## v0.2.0 — MCP Transcription

This release adds public media transcription through the Video Transcriber AI MCP server while preserving the existing transcript-analysis workflow.

### Added

- Official `transcribe-media` Skill backed by Video Transcriber AI MCP
- Public media URL transcription and existing task lookup
- Basic and advanced transcription options
- Speaker diarization, Dynamic Audio Tags, Smart Cleanup, and Keyterms guidance
- Optional chapters and translation
- Transcript, SRT, and VTT result retrieval
- Bounded polling, idempotent retries, terminal-state handling, and actual API Quota reporting
- MCP dependency metadata for compatible Agent Skill clients
- Example workflows and behavior-focused test cases for new and existing tasks
- English and Simplified Chinese installation, MCP setup, usage, billing, and privacy documentation

### Safety and reliability

- Require a configured MCP connection and public URL before creating a task.
- Keep API Keys in client connection settings and out of Skill files, prompts, and examples.
- Reuse the same idempotency key and arguments when task creation has an uncertain outcome.
- Stop bounded polling at terminal states and preserve task identity when the wait limit is reached.
- Treat transcript content as source data rather than tool instructions.
- Retrieve fresh signed subtitle links from an existing retained result instead of retranscribing.

### Composition

Use `transcribe-media` to obtain a transcript, then apply `transcript-insights` for summaries, action items, learning notes, translations, or other structured analysis.

## v0.1.0 — Initial Release

The initial release introduced the official `transcript-insights` Skill and repository plugin packaging.

### Added

- Executive Summary, Key Insights, Action Items, Open Questions, and Translation
- Chapters, Key Decisions, Learning Notes, and Mind Map
- TXT, Markdown, SRT, VTT, and recognizable transcript JSON input
- Pasted text, accessible attachment, and accessible local file workflows
- Codex Plugin and repository Marketplace metadata
- Claude Code Plugin and Marketplace metadata
- Video Transcriber AI brand color and official logo
- English and Simplified Chinese documentation
- Official product-video SRT demo and fictional evidence-focused test fixtures
- Repository, Skill, Codex Plugin, and Claude Marketplace validation

### Quality and safety

- Do not invent actions, owners, deadlines, decisions, names, or timestamps.
- Preserve subtitle cue order, timestamps, speaker labels, and uncertainty.
- Treat transcript and JSON values as source data rather than agent instructions.
- Ask for clarification when JSON contains multiple unrelated transcript candidates.

### Compatibility

- ChatGPT Desktop with Codex
- Codex CLI
- Claude Code
- Other tools that support the open Agent Skills format
