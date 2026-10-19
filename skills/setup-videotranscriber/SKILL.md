---
name: setup-videotranscriber
description: Connect Video Transcriber AI MCP, check an existing connection, or recover from missing tools and API Key errors. Use when a user asks to connect, set up, or troubleshoot Video Transcriber in Codex, ChatGPT Desktop with Codex, Claude Code, or WorkBuddy. Does not require an existing MCP connection.
---

# Connect Video Transcriber

Help the user reach a working connection with the fewest manual steps. Reply in their language, describe the current state simply, and give one actionable next step at a time.

## Connect

1. Discover the current client and any existing Video Transcriber connection. Reuse a healthy connection. Ask which client they use only when the host cannot be identified. Preserve the intended account and environment; clarify an ambiguous account before proceeding.
2. Read only the matching section of [client setup](references/clients.md). The endpoint is `https://videotranscriber.ai/mcp`; authentication is a Bearer API Key. Installing a Skill alone does not supply the credential. This service has no OAuth login flow.
3. When a credential is missing, give one concrete next action: “请登录官网，在 API 控制台获取 Key，然后粘贴到我打开的本地配置窗口，点击连接。我会继续处理刚才的任务。” Link [Video Transcriber AI](https://videotranscriber.ai/). Explain once that transcription uses independent API Quota; website plans do not cover it. Do not initiate a purchase.
4. For local Codex and Claude Code, follow [local setup](references/local-setup.md) and launch the packaged helper for the detected client. It opens a hidden local input, validates the Key, and writes only that client's user-level connection. Prefer this one-paste path over instructions to set environment variables or edit files. A supported native credential dialog is also suitable. The Key stays out of chat, tool arguments, command history, and repository files. Do not read or print the saved config; use the helper's safe status. WorkBuddy and hosted clients use their own supported credential UI as described in [client setup](references/clients.md).
5. Refresh the client connection. The helper's `credential_verified` proves the service accepted the Key; `client_connection_verified: false` means the current Agent still needs to load it. Give the exact client refresh step, retain the original URL/task ID and requested output, and resume after refresh. Verify fresh tool discovery exposes `create_transcription`, `get_transcription`, and `get_transcription_result`. Cached names alone are insufficient. Connection checks never create a paid transcription or prove sufficient quota.
6. Once verified, say the connection is ready and invite a public media URL. If the original request already contained one, resume its requested transcription or analysis through `transcribe-media`; setup alone does not authorize creating a task.

## Recover

For 401 or a revoked Key, use the same local helper with `--replace` or the client's native credential dialog. For a disabled account, direct the user to their API account settings or support. For insufficient quota, explain the separate API balance and link the official site; do not change options, buy quota, or repeatedly submit. For network errors, distinguish endpoint reachability from authentication and preserve existing settings. Cancellation ends setup without changes. If private input is unavailable, give the concrete terminal fallback from local setup rather than only a documentation link. Return a safe status and one next action.

Analyze a user-supplied transcript or subtitle directly without API credentials. If the user asks for a demo and has supplied no transcript, use the [text-only first-run demo](references/first-run.md).
