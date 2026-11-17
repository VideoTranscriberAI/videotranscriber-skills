# OpenClaw connection

Use this guide only when the active host is OpenClaw. The service is `https://videotranscriber.ai/mcp`, using Streamable HTTP and `Authorization: Bearer API_KEY`. The credential is a Video Transcriber API Key from the official site's API console. This endpoint does not provide OAuth sign-in.

## Identify the runtime

Find the Gateway and active profile that run this conversation. The browser, a local terminal, and the Gateway may be on different machines. Configure only the intended Gateway and account. A local desktop client's saved Key does not configure a remote Gateway.

Use OpenClaw's plugin and MCP controls. Do not run `configure_client.py --client openclaw`, select another client's adapter, use `call_mcp.py` to read an OpenClaw config, or parse and rewrite `openclaw.json` as ordinary JSON. Those scripts support the other clients listed in [client setup](clients.md); OpenClaw may use JSON5, named profiles, and remote services.

## Configure the credential privately

The ClawHub bundle declares `Bearer ${VS_API_KEY}`. Supply `VS_API_KEY` to the actual Gateway process, never to the model or chat. Do not retrieve, print, or inspect a user's `.env`, full config, or process environment to find the Key. The operator enters the value privately and the agent checks only safe connection status.

For the normal user-managed environment route:

1. Direct the user to sign in to [Video Transcriber AI](https://videotranscriber.ai/) and create a Key in the API console. Explain once that transcription uses independent API Quota, separate from website credits and unlimited website plans. Do not initiate a purchase.
2. Identify the Gateway's actual state directory. The default is `~/.openclaw`; a named profile normally uses `~/.openclaw-<profile>`. `OPENCLAW_STATE_DIR` and `OPENCLAW_CONFIG_PATH` can select a different instance. Do not infer the remote Gateway's home from the local browser or agent workspace.
3. Have the operator add or update only `VS_API_KEY` in that Gateway's user-level `.env` through their own trusted local editor or deployment secret input. Keep all existing entries. The non-secret format is `VS_API_KEY=<your API Key>`; the real value must never be returned in chat, command arguments, source files, or examples. Restrict the file to the service user (POSIX `0600` or the Windows equivalent). This route is plaintext local configuration, not an encrypted vault.
4. A foreground Gateway must be launched with this environment. A running background service needs its environment reloaded or the Gateway restarted by its operator before the new value is effective. Setting a variable only in the current terminal does not update an existing daemon. For remote or container deployments, configure the service on the machine/container running the Gateway.
5. Existing operator-supplied process values take precedence over the global `.env`. If a replaced Key still appears rejected, check environment precedence with the operator without printing values or repeatedly collecting a Key.

If the operator already uses a working native MCP connection with a supported credential/secret setting, reuse it. Native secret-store entries and skill-scoped environment values are not automatically equivalent to the Gateway process variable consumed by this bundle. Do not promise that typing a Key into an unrelated Skill settings field will configure the MCP connection. Follow the installed OpenClaw version's supported credential binding when using such an override.

## Verify, then continue

Inspect the installed plugin and discover the actual `create_transcription`, `get_transcription`, and `get_transcription_result` tools. OpenClaw may prefix their names, for example `videotranscriber__get_transcription`. Read their current schemas rather than requiring an exact prefixed name.

The operator can inspect plugin detection with:

```bash
openclaw plugins inspect videotranscriber-skills
```

If this server is explicitly configured under `mcp.servers.videotranscriber`, a live configuration probe is:

```bash
openclaw mcp doctor videotranscriber --probe
```

The saved-server CLI and plugin-contributed connections can have different diagnostic surfaces. Do not treat an unknown saved-server name as proof that an installed plugin is broken. Use the installed plugin's runtime status and fresh tool discovery for its contributed connection. Saving a setting or recognizing the bundle does not prove authentication. An authenticated initialize/tool-discovery check creates no transcription and does not prove sufficient API Quota.

If bundled connection detection is unavailable in the installed version, an operator may configure the same service through Settings → MCP with the following non-secret configuration. Preserve other servers and the intended account. A same-name `mcp.servers` entry overrides the plugin entry; avoid duplicate connections.

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

After authentication and fresh discovery, continue the original URL/task request through `transcribe-media`. Setup alone does not authorize a paid task. If tools remain unavailable, report the observed plugin/configuration/runtime blocker and one concrete remedy; do not run an unrelated desktop adapter or write a replacement MCP client. Pure transcript/SRT analysis can continue with `transcript-insights` without a Key or any transcription call.

## Recovery

- Recognized `invalid_api_key` / `api_key_revoked`: have the operator replace the Key through the same private route, then apply it to the correct Gateway and recheck discovery.
- `api_account_disabled`: direct the user to API account settings or support. Changing the Key does not repair a disabled account.
- Generic HTML or unrecognized HTTP 401/403: report a gateway/access-policy rejection; it does not establish that the Key is invalid.
- Timeout, unavailable service, or disconnected tools: perform bounded connection checks and report safe status. Do not create a task as a connectivity test.
- Insufficient quota: stop the paid operation and explain the independent API balance. Do not automatically buy quota, change options, or create another task.
- No Key or skipped setup: keep transcription unavailable and continue existing-text analysis when requested. Never require `VS_API_KEY` for `transcript-insights`.

Reference: [OpenClaw MCP](https://docs.openclaw.ai/tools/mcp), [bundle transports](https://docs.openclaw.ai/plugins/bundles#transports), [environment sources and profiles](https://docs.openclaw.ai/help/environment).
