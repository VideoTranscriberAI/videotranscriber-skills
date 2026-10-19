# Basic transcription example

## Request

```text
帮我转写这个视频，返回全文和 SRT 字幕链接：https://www.youtube.com/watch?v=e8WaTlzuid0
```

This public URL is the official Video Transcriber AI product video. Running this request creates a real task and consumes independent API Quota. It is not a free connection check. For a text-only demo without an API Key, ask “先用示例字幕试一下摘要功能”.

## Expected behavior

- Confirm that the request uses API Quota.
- Create one task with a fresh idempotency key.
- Poll at the server-provided interval and stop at a terminal status.
- Fetch the result only when it is available.
- Report the task ID, transcript, requested subtitle link, and actual usage.
- Do not expose the configured API Key or include a signed download URL in diagnostic output.
