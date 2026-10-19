# First connection

Request:

```text
我已经装好了，帮我连接 Video Transcriber。
```

Expected behavior:

- Identify the current client, or ask one client-selection question when unknown.
- Reuse an existing healthy connection; otherwise guide the client-specific credential entry.
- Explain independent API Quota once. Never request a Key in chat.
- Check authenticated connection status/tool discovery without creating a transcription.
- Clearly distinguish verified access from configuration awaiting verification.
- Invite a public media URL only after connection verification. Offer the text-only demo if the user wants to try analysis first.
