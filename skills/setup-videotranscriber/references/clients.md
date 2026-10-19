# Client connection steps

Read the section for the user's actual client. Official service reference: [MCP overview](https://videotranscriber.ai/code-docs#mcp-overview). The endpoint accepts a fixed API Key, not a website login token or OAuth token.

## ChatGPT Desktop with Codex / Codex

The plugin packages the Skills; the client owns the MCP connection and its credential. If this host provides a credential/settings dialog for Bearer headers, use it to enter the Key. A repo marketplace is not a public directory listing, and these local Codex steps do not establish support in every ChatGPT surface.

Use the client's MCP settings to configure `https://videotranscriber.ai/mcp` with the user's Bearer credential. If there is no credential UI, offer the CLI fallback below, or explain which supported client provides a credential form. Do not instruct the user to enable OAuth for this endpoint.

For a user who chooses terminal setup, collect `VT_API_KEY` using the local prompt at the end of this guide, then run this non-secret registration command:

```bash
codex mcp add videotranscriber --url https://videotranscriber.ai/mcp --bearer-token-env-var VT_API_KEY
```

The equivalent TOML is:

```toml
[mcp_servers.videotranscriber]
url = "https://videotranscriber.ai/mcp"
bearer_token_env_var = "VT_API_KEY"
```

Merge this one entry into the selected config; do not replace the file or an existing differently configured connection. The process running Codex must inherit `VT_API_KEY`. A variable exported in one terminal does not configure an app already launched from the Dock or Start menu. Never write a secret into the plugin package. Refresh/restart the chosen client, then inspect `/mcp` in an interactive Codex session. `codex mcp list` confirms saved entries; it does not by itself prove authenticated tool discovery.

References: [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp), [OpenAI local plugins](https://developers.openai.com/plugins/build/plugins).

## Claude Code

The Claude plugin declares an optional sensitive `api_key` user configuration value and an HTTP MCP server that references it. When the plugin is enabled, a compatible client prompts for **Video Transcriber API Key**. Fill that masked field locally and refresh the connection through `/mcp`. The optional field lets transcript-only users skip connection setup.

If the installed Claude version does not support plugin credential configuration, use user-scoped MCP settings. After the user sets `VT_API_KEY` with the local prompt below, the following registration command stores an environment-variable reference rather than expanding the Key in a shell argument:

```bash
claude mcp add --transport http --scope user videotranscriber https://videotranscriber.ai/mcp --header 'Authorization: Bearer ${VT_API_KEY}'
```

This fallback requires the process running Claude Code to inherit `VT_API_KEY`. Check `/mcp` for a fresh connection and the three tools. Inspect only status, endpoint, and credential presence; avoid printing a full saved configuration. If an existing manual connection already works, reuse it and avoid enabling a duplicate plugin connection.

References: [Claude plugin user configuration](https://code.claude.com/docs/en/plugins-reference#user-configuration), [Claude MCP](https://code.claude.com/docs/en/mcp).

## WorkBuddy

Use the Video Transcriber connection's API Key field if a connector is already installed. This repository includes a Token connector adapter; it does not imply the connector is available in WorkBuddy's market. Do not invent an install link. Maintainer packaging and submission steps are in `docs/WORKBUDDY.md` in the source repository.

For a custom connection, guide the user to WorkBuddy's MCP/connector settings, choose a remote HTTP connection, and set:

```text
URL: https://videotranscriber.ai/mcp
Header name: Authorization
Header value: Bearer <enter the API Key locally>
```

The packaged Token form fills this header automatically. It needs WorkBuddy 4.24.0 or newer because the adapter also includes bilingual usage examples. Save and refresh, then check the connection's authenticated tool list. Field names can vary by client version; inspect the visible controls or request the version when necessary.

Reference: [WorkBuddy connector and Token forms](https://open.workbuddy.cn/docs/connector).

## Local credential prompt for terminal fallback

This optional fallback is for terminal users; prefer the client's masked credential dialog. Open a local terminal, start `bash`, and run:

```bash
read -r -s -p "Video Transcriber API Key: " VT_API_KEY
export VT_API_KEY
printf '\n'
```

Enter the Key at the hidden prompt, then run the matching non-secret registration command above and launch `codex` or `claude` from the same terminal. The Key is not part of command history. This only sets the current shell session; after closing it, enter the Key again or use the client's persistent credential storage. Do not claim this configures an already running desktop app.
