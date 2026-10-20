# One-paste local setup

The packaged `scripts/configure_client.py` supports local Codex, Claude Code, WorkBuddy, Cursor, Windsurf/Cascade, Gemini CLI, GitHub Copilot CLI, VS Code, Cline, and Roo Code. It requires Python 3.11+ and uses the standard library. Use an available host/bundled runtime; do not install system dependencies just to hide a missing-runtime error.

## Launch for the active client

Resolve the script from this installed Skill, not a guessed repository/cache. Select the client from the active host context. Then run, for example:

```bash
python3 scripts/configure_client.py --client cursor --language zh
```

The example assumes the Skill directory is the working directory. In actual tool calls use its absolute installed script path and quote paths. The user should not need to type this command themselves. Change only `--client` for the active application:

| Client | `--client` | User configuration |
| --- | --- | --- |
| Codex | `codex` | `$CODEX_HOME/config.toml` or `~/.codex/config.toml` |
| Claude Code | `claude-code` | `~/.claude.json` |
| WorkBuddy | `workbuddy` | `~/.workbuddy/mcp.json` |
| Cursor | `cursor` | `~/.cursor/mcp.json` |
| Windsurf / Cascade | `windsurf` | Existing legacy `~/.codeium/windsurf/mcp_config.json` or relocated Devin/Cascade config; see below |
| Gemini CLI | `gemini-cli` | `~/.gemini/settings.json` |
| GitHub Copilot CLI | `copilot-cli` | `$COPILOT_HOME/mcp-config.json` or `~/.copilot/mcp-config.json` |
| VS Code user-profile MCP | `vscode` | The active user profile's `mcp.json`; the default is under `Code/User/` in the OS application-data directory |
| Cline | `cline` | Existing `cline_mcp_settings.json`; honors `CLINE_MCP_SETTINGS_PATH` |
| Roo Code | `roo-code` | Existing global `mcp_settings.json` |

`--language en` selects English. `--input auto` opens a hidden macOS system dialog, a masked Windows dialog, or Zenity on Linux when available. The same input mechanism is shared across these clients; the client must allow local process execution and the OS must allow the dialog. Client transport/configuration support has automated coverage; real application behavior must be accepted in each installed client.

Before launch, resolve known host network and user-config write permission requirements. The helper checks local write access before opening private input; a permission error should be handled before asking for another Key. Tell the user: obtain their Key in the official API console, paste it once into the local window, then click Connect. Explain that it is stored in the selected client's local plaintext user configuration with restricted file permissions. Retain the original URL, requested output, and existing task ID.

## Choose the real profile

- VS Code: macOS uses `~/Library/Application Support/Code/User/`, Windows uses `%APPDATA%/Code/User/`, and Linux uses `$XDG_CONFIG_HOME/Code/User/` or `~/.config/Code/User/`. The helper checks installed editor directories and named profiles. When more than one editor variant or any named profile is present, identify the active file explicitly; a sole existing MCP file may belong to an inactive profile. `VSCODE_PORTABLE` is supported. Use `MCP: Open User Configuration` to identify a custom/remote user profile. For the Copilot harness, prefer `--client copilot-cli`, which writes the portable user configuration read directly by Copilot. The `vscode` profile uses the separate top-level `servers` format.
- Cline/Roo Code: the helper checks existing global settings in common VS Code, Insiders, Cursor, Windsurf, and VSCodium user storage, including named profiles. Cline CLI's existing `~/.cline/data/settings/cline_mcp_settings.json` is also recognized. If no file or several files exist, use Cline's MCP Servers → Configure → Configure MCP Servers, or Roo's MCP → Edit Global MCP, to locate the active user file. The Agent supplies that non-secret path using `--config`.
- Windsurf/Cascade: the legacy user path is `~/.codeium/windsurf/mcp_config.json`. Current Devin/Cascade also uses `$XDG_CONFIG_HOME/devin/mcp_config.json` (default `~/.config/devin/mcp_config.json`) on macOS/Linux, or `%APPDATA%/devin/mcp_config.json` on Windows. A single existing match is reused. If both product directories exist, use `--config` to identify the active product even if only one MCP file currently exists. If no file exists, it uses the sole installed product directory, or the legacy Windsurf path when neither directory exists: verify the host is actually Windsurf. For a custom relocated installation, use Open MCP config file and pass its actual path explicitly.
- Claude custom profiles (`CLAUDE_CONFIG_DIR`), remote/WSL extensions, portable editors, and other custom user-data roots: identify the real user config and pass `--config /absolute/user/config`. Never select a project `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, or another repository file for a credential.

`config_selection_required` occurs before opening a Key dialog. Resolve the active path rather than writing into every detected application. Installing a Skill and configuring its client are separate steps.

## Storage and verification

- Codex stores `mcp_servers.<name>.http_headers.Authorization`; JSON clients store `headers.Authorization` in their client-specific server map. Transport fields differ: Windsurf uses `serverUrl`, Gemini CLI uses `httpUrl`, VS Code uses `servers`, and Cline/Roo/WorkBuddy have explicit transport types. The helper handles these differences.
- Existing healthy credentials and uniquely matching connection names are reused. A usable Codex environment reference can be migrated without another paste. `--replace` prompts for one new Key; `--check` checks the saved credential without prompting or writing.
- JSON/JSONC edits preserve unrelated text, comments, settings, and server entries. TOML edits preserve unrelated configuration. Unsupported or conflicting layouts stop before credential entry. Cancellation, invalid credentials, network failure, and concurrent edits preserve the original file. Permissions are POSIX `0600` or an explicit current-user Windows ACL. This is plaintext local storage, not an encrypted vault or a shared credential service across Agents.
- Validation sends credentials only to `https://videotranscriber.ai/mcp`, with TLS verification and no redirects. It uses initialize → initialized notification → tools/list; no paid task is created. A successful check does not prove sufficient API Quota. Transport `auto` prefers an installed curl; otherwise it uses Python's standard HTTP client. No dependency is installed. Curl receives headers and request data through private stdin, with user curl configuration disabled; response data uses an automatically removed private temporary file. Python collects short reads and checks advertised response length. Advanced diagnostics may select `--transport curl` or `--transport urllib` without changing the credential.
- `invalid_key` and `key_revoked` come from recognized API authentication errors. `account_disabled` requires an account-status remedy. `access_blocked` means an unrecognized 401/403, such as a gateway rejection: do not tell the user to create a new Key. Safe error output includes HTTP status and failed operation, never the server's raw body or a credential.
- Validation errors include safe operation/HTTP/content-type or parser-stage metadata when available. Transient failures are retried in the same process, without another paste; permissions, gateway policy, and explicit authentication failures require their own remedy.
- Do not print configuration, environment values, raw HTTP exceptions, or shell tracing. Never pass a secret as `--key`, a command argument, chat input, or a repository file. Advanced `--input env` reads `VS_API_KEY` locally without printing it.

## Continue after validation

`awaiting_key` means use the local input. Yield tool output while a dialog remains open; it times out after five minutes. `retrying_verification` means the same process is retaining the Key only in memory and retrying discovery, at most twice with bounded backoff. Wait for its final status instead of launching another input. Cancellation, invalid/revoked Key, account/access/permission errors, and non-retryable HTTP statuses are not automatically retried. Server-requested backoff is honored; a delay over 30 seconds is reported without an early automatic retry. The Key is never saved merely to enable a retry.

`credential_verified` proves authenticated discovery accepted the Key. `configuration_saved: true` means only that the local file changed. `next_action: discover_client_tools` directs the Agent to check current host discovery/status. `client_connection_verified: false` means the helper has not inspected the host; it does not prove that the host needs refreshing. The compatibility field `reload_required` is `null` after a write because runtime reload requirements are unknown, and `false` when this check changed no configuration. Neither value is a reason to force a manual restart.

First re-discover `create_transcription`, `get_transcription`, and `get_transcription_result` in the active host. If available, continue the original request. A real supported host reload API may load missing native tools; do not try to operate Codex's own window through Computer Use. If native tools remain unavailable, continue through the packaged caller below, using the same official MCP endpoint and saved credential. Retain the original URL/task ID. Connection checks do not create paid tasks.

## Same-session tool calls

Use `scripts/call_mcp.py` from this installed Skill, with the active `--client` and the same `--config` if a custom profile was selected. It reads the saved Key locally, performs authenticated discovery, and calls only `create_transcription`, `get_transcription`, or `get_transcription_result`. It does not prompt for another Key or modify client configuration. This is a direct MCP client, not native host tool registration; explain that distinction only if needed. Do not invent a host reload tool or write a replacement network script.

The Agent runs the command; the user only supplies their media request:

```text
python3 /absolute/installed/setup-videotranscriber/scripts/call_mcp.py --client CLIENT --tool TOOL --arguments 'ACTUAL_JSON_ARGUMENTS'
```

Replace every placeholder before execution. The JSON contains only the tool arguments from the connected contract, never credentials. For creation, generate and retain the actual idempotency key before the first call; reuse the identical JSON on retries or native/caller handoff. For either lookup, use the retained `request_id`. The same process makes at most two automatic transport retries with unchanged arguments and RPC ID. It honors bounded backoff and rejects redirects. Validation/auth/quota/idempotency errors require their specific remedy, never a new creation key.

The caller emits JSON with `status`, `tool`, safe `http_status`/`retry_after`, and the normalized API payload under `result`. `status: completed` only means the operation returned; `result.status` is the transcription state. `status: tool_error` (exit 2) contains the API/tool error. Connection or local errors use `status: error` (exit 1). While `retrying_verification` or `retrying_mcp_call` appears, wait on that process instead of launching a new caller or Key dialog.

For `get_transcription_result`, supply `--output /absolute/new/private-result.json` to preserve a long result without tool-output truncation, then read that file for the requested analysis. Existing files are preserved. Results are bounded to 16 MiB; incomplete/oversized content is reported instead of presented as complete. Download URLs are omitted by default; use `--include-download-links` only for an explicit subtitle/download request, and keep them out of diagnostic logs. Apply the normal `transcribe-media` polling budget and terminal-state rules. No task is created merely to check this path.

## Manual client refresh fallback

If neither native tools nor the packaged caller can be used, explain the actual blocker and give one relevant remedy. The following manual actions apply when refreshing native registration is the chosen remedy; they are not required before using the caller:

| Client | Refresh/check |
| --- | --- |
| Codex | Refresh the server in Settings → MCP servers, or restart Codex if unavailable; inspect the freshly loaded three tools |
| Claude Code | `/mcp`, reconnect the server; restart if the user-scoped entry is not loaded |
| WorkBuddy | Reopen/refresh MCP servers in the connector/plugin settings; check the server status, or restart |
| Cursor | Refresh/enable the server in MCP settings; restart if the updated configuration is not loaded |
| Windsurf/Cascade | Refresh MCP configuration in the Cascade MCP view, or restart |
| Gemini CLI | `/mcp refresh`, then `/mcp list` |
| GitHub Copilot CLI | Inspect `/mcp`; restart the CLI to load changed user configuration |
| VS Code | `MCP: List Servers`, select the server and restart; confirm tools in the active harness |
| Cline / Roo Code | Reconnect/restart this server in the MCP Servers panel; check tool discovery |

Inspect the actual client controls before describing a specific fallback button. Do not claim to reload a client unless the host performed it. If a reload was needed, verify fresh discovery exposes `create_transcription`, `get_transcription`, and `get_transcription_result`. Preserve the original URL/task ID and continue the requested task. If a new conversation is needed, give a short resume message containing only the public URL/request or task ID.

## When a private input window is unavailable

Give the user a ready-to-copy command using the actual installed helper and active client, for their own local terminal:

```bash
python3 /absolute/installed/skill/scripts/configure_client.py --client cursor --input terminal --language zh
```

Include `--config` if the actual profile needed it. Only launch terminal input where the user can type; Agent tool stdin is not a user terminal. The helper refuses noninteractive or echoing terminal input. Native supported credential forms are also suitable. Browser/cloud-only Agents need their own credential UI; a local script cannot configure them remotely.
