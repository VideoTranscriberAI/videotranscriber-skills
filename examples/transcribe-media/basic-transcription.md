# Basic transcription example

## Request

```text
Use $transcribe-media to transcribe https://example.com/media/demo.mp4 with the basic model. Wait for completion, then return the transcript, SRT link, and actual API Quota usage.
```

## Expected behavior

- Confirm that the request uses API Quota.
- Create one task with a fresh idempotency key.
- Poll at the server-provided interval and stop at a terminal status.
- Fetch the result only when it is available.
- Report the task ID, transcript, requested subtitle link, and actual usage.
- Do not expose the configured API Key or include a signed download URL in diagnostic output.
