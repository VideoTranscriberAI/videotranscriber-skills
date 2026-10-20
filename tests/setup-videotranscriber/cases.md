# Connection behavior cases

## New user, no MCP tools

“帮我连接 Video Transcriber” leads to the current client's connection steps. Only ask the client name if it cannot be discovered. Explain the separate API balance, provide the official site and API console navigation, and direct credential entry into local client settings. Do not stop at “configure MCP”, request a Key in chat, or submit a test transcription.

For each supported local client, launch the installed `scripts/configure_client.py` with the matching client argument. Resolve an ambiguous editor/user profile before prompting. Explain that the user pastes once in the hidden local input and that the Key is saved in the client user config as restricted plaintext. Do not ask a beginner to choose environment-variable syntax or reply only with a documentation link. `VS_API_KEY` remains an explicit advanced choice.

## Existing connection

A healthy connection is reused. A saved entry or cached tool name with no fresh authenticated discovery is reported as configured but unverified. Preserve unrelated settings and the user's chosen account.

When the helper returns `credential_verified`, discover the current host tools first. If the three tools are now available, continue the original media request. Otherwise use a real host reload capability if available, then the packaged same-session caller when native tools are still missing. Preserve the URL/task ID and saved Key. No restart or second input is required for this path. Setup alone never authorizes a paid call. Do not operate Codex's own window through Computer Use or write an ad hoc network client.

## Missing client capabilities

When the client cannot edit connection settings or expose fresh tool discovery, provide the exact supported next step and state what remains unverified. Do not claim automatic installation or successful authentication.

If a hidden local window cannot open, provide one copyable command with the resolved script/runtime paths and `--input terminal`, for execution in the user's own terminal. Do not start an inaccessible Agent-terminal prompt, expose the Key via CLI arguments, or fall back to asking for it in chat. A missing runtime or unsupported config layout is reported explicitly.

## Cancel, rejected Key, and concurrent writes

Cancel exits without a new config. Rejected credentials and service/network failure leave existing files unchanged. A same-name connection to a different endpoint requires account/environment selection. Concurrent client edits are preserved. The agent receives only safe status codes and never dumps config or exception response bodies.

## Revoked Key and insufficient quota

Guide Key replacement in the client credential dialog for 401/revoked credentials. For insufficient quota, explain API Quota and the API console; never buy quota, change model/options, or repeatedly create tasks. Connection success does not prove sufficient balance.

## Transcript-only user

Pasted SRT or the first-run text demo is analyzed without requiring an API Key. Skipping optional connection setup must not block text analysis.

## Resume original intent

After an originally requested public-video summary has its connection verified, continue the original transcription-and-analysis request. A setup-only request does not authorize a paid demo. Existing pending tasks are resumed with their original ID, never recreated.

## Gateway rejection and disabled account

A gateway returns 403 with HTML or non-API JSON. Expected: `access_blocked`, preserve the previous config, and give a network/access-policy next step without requesting another Key. A recognized `api_account_disabled` is an account-status problem. Only recognized `invalid_api_key` / `api_key_revoked` responses justify credential replacement. Never echo the response body or secret.

## Client formats and profiles

Run setup against isolated user files for each supported client. Verify its root map, URL field and transport type, preservation of sibling servers/settings/comments, restricted file permissions, and no paid tool call. VS Code uses `servers`, Gemini Streamable HTTP uses `httpUrl`, Windsurf uses `serverUrl`, WorkBuddy/Cline use `streamableHttp`, and Roo uses `streamable-http`. Multiple editor/profile files require choosing the active user config before input. Never write a Key into a project config to make a test pass.

## One paste across transient verification errors

Inject a network failure and an unexpected discovery response, then success. Expected: one credential read, at most three verification attempts in the same process, no unvalidated credential written, safe progress metadata, then save on success. Exhaustion preserves the original file. Cancellation and explicit auth/account/gateway/permission errors stop without automatic replacement. Known write/runner permission failures are resolved before opening private input.

## HTTP completeness and same-session continuation

Exercise valid JSON returned in short reads, premature EOF before Content-Length, curl partial-transfer errors, and a result larger than the discovery limit. Credentials appear only on private stdin, not curl argv/config files; user curl config, redirects and insecure TLS are disabled. Without curl, use Python. Reject incomplete results.

With no native tools/reload API, reuse a saved test credential through the packaged caller and finish the authorized media task. After an uncertain creation, repeat only identical arguments/idempotency key. Quota/validation errors do not recreate the task. Long results use a new private file; preserve existing files and omit signed URLs unless explicitly requested.
