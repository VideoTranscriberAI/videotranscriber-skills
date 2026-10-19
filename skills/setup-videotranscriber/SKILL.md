---
name: setup-videotranscriber
description: Connect Video Transcriber AI MCP, check an existing connection, or recover from missing tools and API Key errors. Use when a user asks to connect, set up, or troubleshoot Video Transcriber in Codex, ChatGPT Desktop with Codex, Claude Code, or WorkBuddy. Does not require an existing MCP connection.
---

# Connect Video Transcriber

Help the user reach a working connection with the fewest manual steps. Reply in their language, describe the current state simply, and give one actionable next step at a time.

## Connect

1. Discover the current client and any existing Video Transcriber connection. Reuse a healthy connection. Ask which client they use only when the host cannot be identified. Preserve the intended account and environment; clarify an ambiguous account before proceeding.
2. Read only the matching section of [client setup](references/clients.md). The endpoint is `https://videotranscriber.ai/mcp`; authentication is a Bearer API Key. Installing a Skill alone does not supply the credential. This service has no OAuth login flow.
3. Direct the user to sign in at [Video Transcriber AI](https://videotranscriber.ai/), open the API console, and create or choose an API Key. Explain once that transcription uses independent API Quota; website credits and unlimited website plans do not cover it. Do not promise a trial grant or initiate a purchase.
4. Prefer the client's credential dialog. The user enters the Key there, never in chat, tool arguments, repository files, or command history. Inspect credential presence rather than reading or displaying a secret. When the host exposes authorized configuration tools, apply only this connection's non-secret settings and preserve unrelated entries. Otherwise give the documented client-specific steps. Do not invent an installation button or claim a configuration change was made.
5. Refresh the connection. Verify fresh, authenticated tool discovery exposes `create_transcription`, `get_transcription`, and `get_transcription_result`. Use client connection status or MCP discovery, never a paid transcription as a connection check. Cached tool names or a saved config alone do not establish authentication. When discovery is unavailable, report “configured; connection not yet verified” and give the exact next check.
6. Once verified, say the connection is ready and invite a public media URL. If the original request already contained one, resume its requested transcription or analysis through `transcribe-media`; setup alone does not authorize creating a task.

## Recover

For 401 or a revoked Key, guide replacement in the same credential dialog. For a disabled account, direct the user to their API account settings or support. For insufficient quota, explain the separate API balance and link the official site; do not change options, buy quota, or repeatedly submit. For network errors, distinguish endpoint reachability from authentication and preserve existing settings. Return only a safe status and next action.

Analyze a user-supplied transcript or subtitle directly without API credentials. If the user asks for a demo and has supplied no transcript, use the [text-only first-run demo](references/first-run.md).
