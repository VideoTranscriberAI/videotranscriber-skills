# Roadmap

## Available

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

## Planned

### Video Transcriber AI API integration

Add one shared Video Transcriber AI API capability so an agent can obtain a transcript from:

- audio
- video
- YouTube URLs
- podcast URLs
- public video URLs

The API workflow will feed transcripts into existing analysis Skills rather than duplicate API clients or transcript-analysis logic. Transcript-only workflows will remain available when the integration is absent. The integration must define authentication, timeout, polling limits, failure, retry, cancellation, and terminal-state behavior before release.

### Candidate Skills

- `subtitle-refinement`: punctuation, line breaks, capitalization, names, speaker labels, and timeline preservation
- `transcript-visuals`: mind maps, infographics, and other transcript-grounded visual outputs
- `transcript-seo`: transcript-grounded titles, descriptions, metadata, and content briefs

Candidate Skills are not committed release promises. They will be evaluated against product scope and overlap before implementation.

Generic site audits, Search Console analysis, competitor research, and other SEO workflows that do not depend on a transcript or Video Transcriber AI product capability are outside this repository.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for Skill boundaries and API integration principles.
