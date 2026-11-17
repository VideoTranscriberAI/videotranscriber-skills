# OpenClaw connection

Use this guide only when the active host is OpenClaw. The service is `https://videotranscriber.ai/mcp`, using Streamable HTTP and `Authorization: Bearer API_KEY`. The credential is a Video Transcriber API Key from the official site's API console. This endpoint does not provide OAuth sign-in.

## Identify the runtime

Find the Gateway and active profile that run this conversation. The browser, a local terminal, and the Gateway may be on different machines. Configure only the intended Gateway and account. A local desktop client's saved Key does not configure a remote Gateway.

Use OpenClaw's plugin and MCP controls. Do not run `configure_client.py --client openclaw`, select another client's adapter, use `call_mcp.py` to read an OpenClaw config, or parse and rewrite `openclaw.json` as ordinary JSON. Those scripts support the other clients listed in [client setup](clients.md); OpenClaw may use JSON5, named profiles, and remote services.

## Configure the Gateway connection and credential

For a new connection using this bundle's environment template, the required setup has two parts: supply `VS_API_KEY` to the actual Gateway process and explicitly configure `mcp.servers.videotranscriber` through OpenClaw's native MCP settings. The same-name Gateway entry overrides the bundled connection and lets the Gateway configuration loader expand `Bearer ${VS_API_KEY}`. Installing the bundle and setting the environment variable alone do not complete this binding.

Keep the credential out of the model and chat. Do not retrieve, print, or inspect a user's `.env`, full config, or process environment to find the Key. The operator enters the value privately and the agent checks only safe connection status.

Complete both configuration steps for the intended Gateway/profile:

1. Direct the user to sign in to [Video Transcriber AI](https://videotranscriber.ai/) and create a Key in the API console. Explain once that transcription uses independent API Quota, separate from website credits and unlimited website plans. Do not initiate a purchase.
2. Identify the Gateway's actual state directory. The default is `~/.openclaw`; a named profile normally uses `~/.openclaw-<profile>`. `OPENCLAW_STATE_DIR` and `OPENCLAW_CONFIG_PATH` can select a different instance. Do not infer the remote Gateway's home from the local browser or agent workspace.
3. Have the operator add or update only `VS_API_KEY` in that Gateway's user-level `.env` through their own trusted local editor or deployment secret input. Keep all existing entries. The non-secret format is `VS_API_KEY=<your API Key>`; the real value must never be returned in chat, command arguments, source files, or examples. Restrict the file to the service user (POSIX `0600` or the Windows equivalent). This route is plaintext local configuration, not an encrypted vault.
4. Use OpenClaw's native MCP settings/configuration controls to add or update `mcp.servers.videotranscriber` using the non-secret configuration below. Merge only this entry, preserve other servers and settings, and keep `${VS_API_KEY}` as a literal reference. Reuse the same server name so the Gateway entry overrides the bundle; do not create a duplicate connection.
5. Apply the configuration to the actual Gateway/profile. A foreground Gateway must be launched with this environment. A running background service needs its environment reloaded or the Gateway restarted by its operator before the new values are effective. Setting a variable only in the current terminal does not update an existing daemon. For remote or container deployments, configure the service on the machine/container running the Gateway.
6. Existing operator-supplied process values take precedence over the global `.env`. If a replaced Key still appears rejected, check environment precedence and the required native MCP binding with the operator without printing values or repeatedly collecting a Key.

Required native Gateway connection (merge into the active configuration through OpenClaw's controls):

```json
{
  "mcp": {
    "servers": {
      "videotranscriber": {
        "url": "https://videotranscriber.ai/mcp",
        "transport": "streamable-http",
        "headers": {"Authorization": "Bearer ${VS_API_KEY}"}
      }
    }
  }
}
```

If the operator already uses a working native MCP connection with a supported credential/secret setting, reuse it instead of replacing that credential binding. Verify that it supplies the same service and that authenticated discovery succeeds. Native secret-store entries and skill-scoped environment values are not automatically equivalent to the Gateway process variable consumed by this bundle. Do not promise that typing a Key into an unrelated Skill settings field will configure the MCP connection. Follow the installed OpenClaw version's supported credential binding when using such an override.

## Verify, then continue

Inspect the installed plugin and discover the actual `create_transcription`, `get_transcription`, and `get_transcription_result` tools. OpenClaw may prefix their names, for example `videotranscriber__get_transcription`. Read their current schemas rather than requiring an exact prefixed name.

The operator can inspect plugin detection with:

```bash
openclaw plugins inspect videotranscriber-skills
```

After the required `mcp.servers.videotranscriber` entry has been applied, run a live configuration probe:

```bash
openclaw mcp doctor videotranscriber --probe
```

Plugin inspection verifies bundle detection; the MCP probe checks the explicit Gateway server. An unknown saved-server name means the required native entry must be checked in the active Gateway/profile. Saving a setting or recognizing the bundle does not prove authentication. An authenticated initialize/tool-discovery check creates no transcription and does not prove sufficient API Quota.

After authentication and fresh discovery, continue the original URL/task request through `transcribe-media`. Setup alone does not authorize a paid task. If tools remain unavailable, report the observed plugin/configuration/runtime blocker and one concrete remedy; do not run an unrelated desktop adapter or write a replacement MCP client. Pure transcript/SRT analysis can continue with `transcript-insights` without a Key or any transcription call.

## Recovery

For any authentication failure, first confirm the active Gateway/profile and both required bindings through safe status checks, without reading or printing the credential. Then handle the reported service error:

- Recognized `invalid_api_key` / `api_key_revoked`: have the operator replace the Key through the same private route, then apply it to the correct Gateway and recheck discovery.
- `api_account_disabled`: direct the user to API account settings or support. Changing the Key does not repair a disabled account.
- Generic HTML or unrecognized HTTP 401/403: report a gateway/access-policy rejection; it does not establish that the Key is invalid. Check that both the Gateway environment binding and the same-name native MCP entry were applied before asking for a replacement Key. A literal placeholder reaching the service is a configuration failure.
- Timeout, unavailable service, or disconnected tools: perform bounded connection checks and report safe status. Do not create a task as a connectivity test.
- Insufficient quota: stop the paid operation and explain the independent API balance. Do not automatically buy quota, change options, or create another task.
- No Key or skipped setup: keep transcription unavailable and continue existing-text analysis when requested. Never require `VS_API_KEY` for `transcript-insights`.

Reference: [OpenClaw MCP](https://docs.openclaw.ai/tools/mcp), [bundle transports](https://docs.openclaw.ai/plugins/bundles#transports), [environment sources and profiles](https://docs.openclaw.ai/help/environment).
