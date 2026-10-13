# MCP tool contract

Use the connected schema for exact validation. All three tools use the connection's Bearer API Key; cookies, API signatures, and credentials in tool arguments are unnecessary.

## create_transcription

| Argument | Default / constraints |
| --- | --- |
| `source_url` | Required public HTTP(S) media URL, at most 4,096 characters. Platform support is determined by the service; an arbitrary webpage is not necessarily media. |
| `idempotency_key` | Required, 1–128 printable ASCII characters without spaces. Unique per intended task; unchanged for retries. |
| `language` | `auto`, or a language code such as `en` or `zh`. |
| `transcription_model` | `basic` or `advanced`; default `basic`. |
| `speaker_diarization` | Boolean, default false. |
| `include_audio_events` | Boolean, default false; requires advanced. |
| `cleanup_speech` | Boolean, default false; requires advanced. |
| `keyterms` | Optional list, requires advanced when nonempty. Maximum 1,000 items, 50 characters each; no commas or phrases longer than 5 words. |
| `chapters` | Boolean, default false; extra API Quota. |
| `target_language` | Optional translation language code; cannot be `auto`; extra API Quota. |

Pass `chapters` and `target_language` as flat MCP arguments. Do not pass the OpenAPI nested `features` object.

The service bills rounded-up media minutes with a minimum of one minute. Current per-minute API Quota: basic 1, advanced 3, nonempty advanced keyterms +1, chapters +1, translation +1. Use the server's actual usage as the final charge; do not confuse API Quota with website transcription credits. If pricing is unknown or has changed, avoid promising an exact total.

Creation returns a task object with `id`, `status`, and `retry_after`. A new request normally reports `_meta.http_status = 202`. An identical idempotent replay can report 200 and the existing task. It is not a newly created task.

## get_transcription / get_transcription_result

Both accept only `request_id`, matching `^req_[0-9a-f]{32}$`.

Status includes task status, `result_available`, `result_expires_at`, `duration_seconds`, `billable_minutes`, `usage`, feature statuses, and any task error. Never follow `poll_url` or `result_url` as a different service when the MCP tools already provide these operations.

Results include `transcript.text`, timestamped `transcript.segments`, optional `transcript.audio_events`, chapters and translation, and subtitle file entries under `files.subtitles.srt` / `files.subtitles.vtt`. Subtitle entries contain `url` and `url_expires_at`. These URLs may expire before `result_expires_at`.

## Error decisions

| Error / response | Action |
| --- | --- |
| `invalid_api_key`, authentication HTTP 401/403 | Stop; ask the user to check the configured credential/account. Never request that a secret be pasted into chat. |
| Validation error, possibly text only | Explain the invalid field. Never send unresolved placeholders such as `{{test_audio_url}}`. |
| `idempotency_conflict` / 409 | The same key was used with different arguments. Preserve the original task; do not retry with a fresh key automatically. |
| `request_not_found` / 404 | Check task ID and selected environment/account. Do not claim the task never existed or disclose another account's data. |
| `insufficient_quota` | Stop and explain; do not silently downgrade or repeatedly submit. |
| `result_not_ready` | Recheck task status within the waiting budget. |
| `result_expired` | Explain the retention limit; a new paid submission needs user instruction. |
| Rate limit, retryable timeout, or service error | Honor backoff and bounded retry. A creation timeout may have accepted the task: reuse the original key and arguments. |

When a tool returns `isError: true`, do not interpret text content as a successful transcript. Error trace IDs identify diagnostics, not transcription tasks.
