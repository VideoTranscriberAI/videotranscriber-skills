---
name: transcript-insights
description: Turn transcripts and subtitles into summaries, key insights, action items, open questions, translations, chapters, decisions, learning notes, and mind maps. Use for pasted text, TXT, Markdown, SRT, VTT, transcript JSON, or requests to summarize a public media URL that can first be handed to transcribe-media. Existing text analysis requires no MCP connection.
---

# Transcript Insights

Transform transcript content into the exact structured outputs the user requests while preserving meaning, evidence, speakers, and available timing information.

## Workflow

1. Identify the transcript source:
   - Use pasted transcript or subtitle text directly.
   - Read attached TXT, Markdown, SRT, VTT, or JSON transcript files when the host provides them.
   - Read a local file path only when the host grants filesystem access.
   - For a public media URL without a transcript, use `transcribe-media` when available to obtain the text, then continue the original analysis request. Briefly explain that this uses independent API Quota. If the MCP connection is missing, use `setup-videotranscriber` when available to guide connection first and retain the original request. Do not ask the user to manually copy a transcript between Skills.
   - If transcription/setup capability is absent, explain the missing capability and offer the [connection guide](https://videotranscriber.ai/code-docs#mcp-overview) or supplied transcript input. Do not invent video content or claim transcription happened.
   - Local/private media cannot be uploaded by these MCP tools. Ask for existing transcript text or a supported public media URL; do not publish the file to make one.
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

Use actual `transcribe-media` capability for public media before analysis. Keep transcription and its retries in that Skill. If the user already supplied a transcript or subtitles, analyze that content directly without requesting an API Key, creating a task, or switching to a demo. Only use source text retrieved or supplied in this conversation; failed or incomplete transcription is not permission to fabricate a summary.
