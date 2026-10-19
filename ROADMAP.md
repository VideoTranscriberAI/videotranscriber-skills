# Roadmap

## Available

### setup-videotranscriber

Client-aware connection and credential guidance, non-billable authenticated tool discovery, and recovery for missing tools or invalid credentials. Existing transcripts remain usable without an API Key.

The setup Skill guides local Codex MCP configuration, and the Claude plugin includes a sensitive credential field. WorkBuddy Token connector and per-skill upload packages can be built from the canonical sources; market publication and target-client installation testing are separate from package validation.

### transcribe-media

MCP-backed transcription for public audio, video, supported platform URLs, and existing Video Transcriber AI task IDs.

The workflow provides bounded polling, idempotent task creation, transcript and subtitle retrieval, optional advanced features, and explicit API Quota handling.

### transcript-insights

Instruction-only analysis for pasted text, attached files, and accessible local TXT, Markdown, SRT, VTT, or recognizable transcript JSON files.

Supported outputs:

- Executive Summary
- Key Insights
- Action Items
- Open Questions
- Translation
- Chapters
- Key Decisions
- Learning Notes
- Mind Map

`transcribe-media` can feed retrieved transcript content into `transcript-insights`. Transcript-only analysis remains available without an MCP connection.

## Planned

### Candidate Skills

- `subtitle-refinement`: punctuation, line breaks, capitalization, names, speaker labels, and timeline preservation
- `transcript-visuals`: mind maps, infographics, and other transcript-grounded visual outputs
- `transcript-seo`: transcript-grounded titles, descriptions, metadata, and content briefs

Candidate Skills are not committed release promises. They will be evaluated against product scope and overlap before implementation.

Generic site audits, Search Console analysis, competitor research, and other SEO workflows that do not depend on a transcript or Video Transcriber AI product capability are outside this repository.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for Skill boundaries and API integration principles.
