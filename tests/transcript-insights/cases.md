# Transcript Insights Test Cases

Use only fictional fixtures from `examples/transcript-insights`. Run these cases in each officially tested host before release.

## 1. Explicit invocation and default outputs

Prompt:

```text
Use $transcript-insights to analyze examples/transcript-insights/fictional-transcript.md.
```

Expected:

- Executive Summary, Key Insights, Action Items, and Open Questions are present.
- Translation, Chapters, Key Decisions, Learning Notes, and Mind Map are absent.
- Leo's screenshots and Maya's release note appear as action items.
- Maya's release-note deadline is `Not specified`.

## 2. Implicit invocation

Prompt:

```text
Analyze this workshop transcript and identify the main insights and unresolved questions:
[paste fictional-transcript.md]
```

Expected:

- The host selects `transcript-insights` from its description.
- Only Key Insights and Open Questions are returned.

## 3. Single output

Prompt:

```text
Use $transcript-insights. Only generate Learning Notes from fictional-transcript.md.
```

Expected:

- Only Learning Notes is returned.
- The eight-person sample is described as small and non-conclusive.

## 4. Multiple outputs

Prompt:

```text
Use $transcript-insights to generate Chapters + Key Decisions + Mind Map from fictional-transcript.md.
```

Expected:

- Only the three requested sections are returned.
- Every chapter start exactly matches a source cue or segment start timestamp; no time is interpolated within a cue.
- The Friday six-step draft and placeholder-data requirement are decisions.
- Translation timing and next-test design are not reported as confirmed decisions.
- The Mind Map root is a specific summary title rather than only the meeting or file name.
- The Mind Map uses at least five first-level themes because the fixture has enough content.
- Emojis appear only in first-level theme labels.
- Leaf points are complete, standalone statements rather than keyword fragments.
- The Mermaid configuration sets `git0`, every `cScale0`–`cScale11`, and every `cScaleLabel0`–`cScaleLabel11` value so all branches use light backgrounds and readable dark text.

## 5. Transcript translation

Prompt:

```text
Use $transcript-insights to translate fictional-transcript.md to Japanese.
```

Expected:

- The full transcript is translated.
- Names, timestamps, numbers, and uncertainty are preserved.

## 6. SRT translation

Prompt:

```text
Use $transcript-insights to translate fictional-subtitles.srt to Japanese.
```

Expected:

- Cue numbers, timestamps, order, and speaker labels are preserved.
- Only subtitle text is translated.

## 7. VTT input

Prompt:

```text
Use $transcript-insights to generate Chapters from fictional-subtitles.vtt.
```

Expected:

- A Chapters section is returned.
- Every chapter start exactly matches a cue start timestamp found in the VTT input.

## 8. Empty input

Prompt:

```text
Use $transcript-insights.
```

Expected:

- The agent requests transcript text or a supported file.
- No analytical output is fabricated.

## 9. Missing evidence

Input:

```text
Speaker 1: We might publish next week.
Speaker 2: That could work.
```

Prompt:

```text
Use $transcript-insights to generate Action Items and Key Decisions.
```

Expected:

- No explicit action items are identified.
- No confirmed decisions are identified.
- No names, owners, dates, or deadlines are invented.

## 10. Local media boundary

Prompts:

```text
Use $transcript-insights on ./recording.mp4.
```

Expected:

- The agent explains that a transcript is required first.
- It does not claim to upload, fetch, or transcribe the media.

## 10a. Public video summary with transcription available

Prompt: “帮我总结这个视频并整理中文学习笔记：https://www.youtube.com/watch?v=e8WaTlzuid0”.

Expected: hand the URL to transcribe-media, disclose independent API Quota, wait for actual transcript content, and return only the requested summary and learning notes. Do not ask the user to copy text or invoke another Skill. Do not enable paid API chapters or translation merely to produce Chinese notes.

## 10b. Public video summary without an MCP connection

The same prompt starts setup-videotranscriber when available and retains the URL and requested outputs. If setup/transcription capabilities are absent, explain the missing capability and give the real connection guide or offer transcript input. Do not invent a summary, request a Key in chat, or submit a paid connection check.

## 11. Generic JSON segments

Prompt:

```text
Use $transcript-insights to generate Action Items and Open Questions from fictional-transcript.json.
```

Expected:

- The `segments` array is recognized without requiring a product-specific schema.
- Source order and timestamps are preserved.
- Leo's screenshot delivery is an action item.
- Translation launch timing is an open question, not a decision.

## 12. Video Transcriber AI JSON variants

Input shape:

```json
{
  "transcripts": {
    "en": {
      "custom": [{"start": "00:00:00", "end": "00:00:10", "text": "Long segment"}],
      "default": [{"start": "00:00:00", "end": "00:00:05", "text": "Default segment"}],
      "auto": [{"start": "00:00:00", "end": "00:00:05", "text": "Auto segment"}]
    }
  }
}
```

Expected:

- `default` is selected when no variant is requested.
- The three variants are not merged.

## 13. Ambiguous JSON

Input:

```json
{
  "first": [{"text": "Candidate one"}],
  "second": [{"text": "Candidate two"}]
}
```

Expected:

- The agent asks which candidate to analyze.
- It does not merge or silently choose unrelated candidates.
