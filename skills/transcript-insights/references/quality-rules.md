# Quality Rules

## Source Fidelity

- Base every factual statement on the supplied transcript.
- Separate explicit statements from reasonable synthesis.
- Preserve uncertainty, disagreement, and conditional language.
- Do not use outside knowledge to fill transcript gaps unless the user explicitly requests external research; label external information separately when research is performed.

## No Fabrication

Never invent:

- action items, owners, or deadlines
- decisions or agreement
- names, roles, or speaker identities
- dates, timestamps, quotations, numbers, or sources
- chapter timecodes
- definitions, examples, or conclusions absent from the transcript

Use `Not specified`, `Unclear from the transcript`, or an equivalent concise statement when information is missing.

## Evidence and Traceability

- Include timestamps when reliable source timestamps are available and useful.
- For chapter starts, use only timestamps that exactly match a source cue or segment start. Never estimate a time within a cue.
- Attribute claims to named speakers or source labels only when the attribution is explicit.
- Do not guess who an unlabeled speaker is.
- Paraphrase by default. Use short quotations only when exact wording materially matters.

## Transcript Cleanup

- Ignore filler words, repeated fragments, cue numbers, and obvious transcription artifacts when they do not affect meaning.
- Allow overlapping subtitle or JSON segment timestamps and preserve source order. Do not delete text solely because time ranges overlap.
- Preserve ambiguous wording instead of silently correcting it into a new claim.
- Retain speaker changes and timestamps when required for subtitles, translation, chapters, or traceability.
- Do not modify the source file unless the user explicitly asks for a rewritten artifact.

## Insufficient Input

- Empty input: ask for transcript text or a supported file.
- Unreadable path or attachment: state that it cannot be accessed and request an accessible file or pasted text.
- Unrecognized or ambiguous JSON: report the schema problem and request a supported transcript field or segment array.
- Very short input: produce only outputs supported by the available content and disclose the limitation.
- Public media URL: follow the main Skill's transcribe-media/setup handoff, then analyze actual retrieved text. When that capability is unavailable, offer the connection guide or request a transcript. Local/private media still requires supplied text or a supported public URL. Never pretend transcription occurred.

## Final Check

Before responding, verify:

1. Every requested output is present.
2. No unrequested output was added.
3. Claims, names, actions, decisions, and times are supported.
4. Missing information is marked instead of guessed.
5. The output language and subtitle formatting match the request.
