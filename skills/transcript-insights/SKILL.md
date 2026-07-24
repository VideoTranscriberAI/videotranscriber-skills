---
name: transcript-insights
description: Turn transcripts and subtitles into structured knowledge, including executive summaries, key insights, action items, open questions, translations, chapters, key decisions, learning notes, and mind maps. Use when the user pastes transcript text, attaches or references a TXT, Markdown, SRT, VTT, or transcript JSON file, or asks to analyze, summarize, translate, organize, study, or extract decisions and follow-ups from a meeting, interview, lecture, podcast, video transcript, or subtitle file. Do not use for raw audio, video, or URL transcription until a transcript is available.
---

# Transcript Insights

Transform transcript content into the exact structured outputs the user requests while preserving meaning, evidence, speakers, and available timing information.

## Workflow

1. Identify the transcript source:
   - Use pasted transcript or subtitle text directly.
   - Read attached TXT, Markdown, SRT, VTT, or JSON transcript files when the host provides them.
   - Read a local file path only when the host grants filesystem access.
   - If the input is raw audio, video, or a URL without a transcript, explain that transcription is required first and stop.
2. For JSON input, read [references/json-input.md](references/json-input.md) and select one transcript candidate without merging alternatives.
3. Validate the input. If it is empty, unreadable, or too incomplete for the requested output, state what is missing and ask for usable transcript content.
4. Detect the requested output types and target language. Read [references/output-types.md](references/output-types.md) whenever choosing formats or combining outputs.
5. If the user does not request specific outputs, generate only:
   - Executive Summary
   - Key Insights
   - Action Items
   - Open Questions
6. Preserve timestamps and speaker labels when they help trace an output back to the source. Ignore subtitle sequence numbers and formatting noise during analysis.
7. Apply [references/quality-rules.md](references/quality-rules.md) before writing the answer.
8. Return only the requested sections in a clear Markdown structure. Match the user's language unless a translation target or another output language is specified.

## Output Selection

Support these output types:

- Executive Summary
- Key Insights
- Action Items
- Open Questions
- Translation
- Chapters
- Key Decisions
- Learning Notes
- Mind Map

Treat natural-language combinations as equivalent to the names above. Do not add unrequested sections. If the user asks for an unsupported transformation, say it is outside the current output set and offer the closest supported options without silently substituting one.

## Translation

- Ask for the target language when it cannot be inferred.
- If Translation is the only requested output, translate the transcript.
- If Translation is combined with analytical outputs, generate the requested outputs in the target language unless the user explicitly asks to translate the full transcript as well.
- Preserve SRT/VTT timestamps and cue boundaries when the user requests translated subtitles.
- Preserve names, technical terms, numbers, uncertainty, and speaker attribution. Do not localize facts.

## Input Boundaries

Accept transcript content through pasted text, accessible attachments, or accessible local file paths. Supported formats are TXT, Markdown, SRT, VTT, and recognizable transcript JSON.

Do not claim to upload, transcribe, download, or fetch audio, video, YouTube, podcast, or public media URLs without an available transcription capability. When such an input is provided, request a transcript or explain that a future Video Transcriber AI API integration can supply it.
