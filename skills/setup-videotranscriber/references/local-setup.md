# One-paste local setup

Use the bundled `scripts/configure_client.py` for local Codex and Claude Code. This is a local configuration helper, not another MCP server. It uses Python 3.11+ with no third-party packages. Identify an available Python runtime before launching it; use the host's bundled runtime when available. Do not install or upgrade system dependencies merely to hide a missing-runtime failure.

## Launch for the actual client

Resolve the script from this installed Skill's directory, not a guessed checkout or cache version. Run it as an argument array when the host supports one; quote executable and script paths in a shell. These example relative paths assume the Skill directory is the working directory:

```bash
python3 scripts/configure_client.py --client codex --language zh
```

```bash
python3 scripts/configure_client.py --client claude-code --language zh
```

Choose `--language en` for English. The default `--input auto` uses a hidden macOS system dialog, a Windows password dialog, or Zenity on Linux when available. The user pastes the Key into that local window and selects Connect. Existing valid saved credentials are reused without another paste. A usable environment-based Codex credential can be migrated to persistent client configuration without another paste.

Before launching, explain the next action in the user's language and say that the Key is saved in their client's local plaintext user configuration with restricted file permissions. Keep the original video URL, output request, and existing task ID available. Only ask which client they use when it cannot be identified.

## Storage and boundaries

- Codex: `$CODEX_HOME/config.toml`, or `~/.codex/config.toml` by default. Store the Bearer header under `mcp_servers.videotranscriber.http_headers`.
- Claude Code: the user-scoped `~/.claude.json`, under `mcpServers.videotranscriber.headers`. User-scoped settings take precedence over plugin MCP entries. Check for local/project/managed connections shadowing the user entry before claiming the current session is ready.
- An explicit `--config <user-config-path>` supports a selected custom profile. A custom `CLAUDE_CONFIG_DIR` requires verifying its actual user config path first; the helper does not guess. Never choose a project `.mcp.json` or repository file to store the Key.
- The helper preserves unrelated settings, refuses a same-name connection to another endpoint, validates before writing, and checks for concurrent edits before atomic replacement. Failed validation and cancellation keep the previous config. Config files get POSIX mode `0600`, or an explicit current-user Windows ACL.
- This is plaintext local storage, not an encrypted vault or a cross-Agent credential service. Each client is configured separately. A different OS user or sufficiently privileged local program may access credentials; do not promise that a model with unrestricted local access can never read them.
- The helper sends the Key only to `https://videotranscriber.ai/mcp`, uses normal TLS verification, rejects HTTP redirects, and performs only initialization and tool discovery. It never submits transcription or tests quota by creating a task.
- Do not `cat` the config, call a raw config-dump command, print environment contents, run shell tracing, or use `--key <secret>`. A user may choose to reuse `VS_API_KEY` via `--input env`; the helper reads it locally and persists it without putting its value in arguments or output.

## Interpret results and refresh

The helper emits JSON status only. `awaiting_key` means the user should use the local input, not reply with a Key. Run a long-lived tool call with output yielding while the dialog is open; the dialog times out after five minutes. Do not open repeated dialogs while one is pending.

`credential_verified` means authenticated MCP discovery succeeded against the service. `configuration_saved: true` and `reload_required: true` mean the local file changed. `client_connection_verified: false` deliberately does not claim that the Agent's running session has loaded it.

- Codex desktop: refresh/restart the connection in Settings → MCP servers. If a reload action is unavailable, restart the client. In an interactive session, inspect `/mcp` afterward. Do not claim to have restarted a client unless the host actually performed it.
- Claude Code: open `/mcp`, select the Video Transcriber connection and reconnect; restart Claude Code if the new user entry has not appeared. Avoid enabling another duplicate plugin connection. Native discovery after refresh confirms the running client loaded the credential.
- If restarting changes the conversation, provide a short resume message containing the original public URL/output request or task ID, never the Key. Continue the same task; connection success alone does not authorize a paid demo.

`--check` verifies an existing configured credential without opening a dialog or rewriting configuration. `--replace` asks for one new Key locally and replaces this connection only after successful validation.

## When a local window cannot open

For `input_unavailable`, give the user a ready-to-copy command with the actual installed script path and available Python executable, for example:

```bash
python3 /absolute/installed/skill/scripts/configure_client.py --client codex --input terminal --language zh
```

The user runs it in their own local terminal and pastes once at the hidden prompt. Do not launch terminal input in an Agent tool session that the user cannot type into. The helper refuses noninteractive or echoing terminal input. After success, give the refresh step above and continue the original request. A browser/cloud-only host without local execution needs its own credential UI; this script is not a universal hosted-Agent install path.

For `invalid_key`, ask the user to copy an active Key from their API console and run `--replace`. For network/service failure, retry the check after connectivity recovers without changing credentials. For `config_changed`, rerun after the other client finishes writing. For `config_conflict`, confirm the intended account/environment rather than overwriting another endpoint. For an unsupported config layout or missing runtime, explain the specific limitation and offer the client's actual credential settings; do not invent a button or promise automatic setup.

References: [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers), [Claude Code user scope](https://code.claude.com/docs/en/mcp#user-scope).
