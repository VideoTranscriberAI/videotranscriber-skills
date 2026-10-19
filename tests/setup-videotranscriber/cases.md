# Connection behavior cases

## New user, no MCP tools

“帮我连接 Video Transcriber” leads to the current client's connection steps. Only ask the client name if it cannot be discovered. Explain the separate API balance, provide the official site and API console navigation, and direct credential entry into local client settings. Do not stop at “configure MCP”, request a Key in chat, or submit a test transcription.

## Existing connection

A healthy connection is reused. A saved entry or cached tool name with no fresh authenticated discovery is reported as configured but unverified. Preserve unrelated settings and the user's chosen account.

## Missing client capabilities

When the client cannot edit connection settings or expose fresh tool discovery, provide the exact supported next step and state what remains unverified. Do not claim automatic installation or successful authentication.

## Revoked Key and insufficient quota

Guide Key replacement in the client credential dialog for 401/revoked credentials. For insufficient quota, explain API Quota and the API console; never buy quota, change model/options, or repeatedly create tasks. Connection success does not prove sufficient balance.

## Transcript-only user

Pasted SRT or the first-run text demo is analyzed without requiring an API Key. Skipping optional connection setup must not block text analysis.

## Resume original intent

After an originally requested public-video summary has its connection verified, continue the original transcription-and-analysis request. A setup-only request does not authorize a paid demo. Existing pending tasks are resumed with their original ID, never recreated.
