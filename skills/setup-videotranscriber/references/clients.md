# Client connection steps

Read the row/section for the active host. Service: `https://videotranscriber.ai/mcp`, using `Authorization: Bearer API_KEY`. The Key comes from the official API console. Website login tokens and OAuth login are not used for this endpoint.

## Local clients: one-paste setup

Use [the packaged helper](local-setup.md), choosing the active client's argument:

| Client | Argument | Connection representation | Official configuration reference |
| --- | --- | --- | --- |
| Codex | `codex` | TOML `mcp_servers`, `http_headers` | [OpenAI Docs](https://learn.chatgpt.com/docs/extend/mcp) |
| Claude Code | `claude-code` | JSON `mcpServers`, `type: http` | [Claude MCP](https://code.claude.com/docs/en/mcp#user-scope) |
| WorkBuddy | `workbuddy` | JSON `mcpServers`, `type: streamableHttp` | [WorkBuddy MCP](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide), [connector format](https://open.workbuddy.cn/docs/connector) |
| Cursor | `cursor` | JSON/JSONC `mcpServers`, `url` | [Cursor MCP](https://cursor.com/docs/mcp) |
| Windsurf/Cascade | `windsurf` | JSON/JSONC `mcpServers`, `serverUrl` | [Cascade MCP](https://docs.devin.ai/desktop/cascade/mcp) |
| Gemini CLI | `gemini-cli` | JSON `mcpServers`, `httpUrl` for Streamable HTTP | [Gemini MCP](https://geminicli.com/docs/tools/mcp-server/) |
| GitHub Copilot CLI | `copilot-cli` | JSON `mcpServers`, `type: http`, tool list | [Copilot CLI MCP](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers) |
| VS Code profile | `vscode` | JSONC `servers`, `type: http` | [VS Code MCP formats](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) |
| Cline | `cline` | JSON `mcpServers`, `type: streamableHttp` | [Cline MCP](https://docs.cline.bot/mcp/mcp-overview) |
| Roo Code | `roo-code` | JSON `mcpServers`, `type: streamable-http` | [Roo MCP](https://roocodeinc.github.io/Roo-Code/features/mcp/using-mcp-in-roo/) |

The helper is the default for local hosts that permit process execution. It opens the OS private-input window and saves only the selected client. Resolve custom profiles before prompting, using the client's own Open User/Global MCP configuration action when necessary. If the current VS Code session uses the Copilot harness, prefer the portable Copilot user profile (`copilot-cli`). Workspace policies, trust prompts, disabled tools, custom profiles, and remote execution can still affect the running client's connection; saved configuration alone does not prove readiness.

Do not infer runtime support from these format adapters alone: verify application-level behavior in the actual installed client. Skills must also be installed in a location the active host discovers. Ask for the client only when the actual host context does not identify it.

## Native forms and hosted clients

Use a real native Key form when it is available. Claude's plugin may expose **Video Transcriber API Key**. An installed WorkBuddy Token connector can expose the same one-paste form and inject the Bearer header. The repository's connector package does not imply a public marketplace listing. Its packaging/submission process is in `docs/WORKBUDDY.md` in the source repository.

For a local host that cannot run the helper, guide its actual custom MCP form with the service URL, Streamable HTTP transport, and Authorization header; enter the Key in the local form. Do not invent a universal Add/Install button or request the Key in chat. Browser/cloud-only clients require their own supported credential UI and cannot use the local helper as a remote setup mechanism. These Codex steps do not establish support in every ChatGPT surface.

## Advanced: environment-based setup

Offer only if the user explicitly chooses environment setup. The default one-paste helper persists the selected client's header and avoids desktop environment inheritance issues.

Codex non-secret registration command:

```bash
codex mcp add videotranscriber --url https://videotranscriber.ai/mcp --bearer-token-env-var VS_API_KEY
```

Claude Code non-secret registration command (literal variable reference):

```bash
claude mcp add --transport http --scope user videotranscriber https://videotranscriber.ai/mcp --header 'Authorization: Bearer ${VS_API_KEY}'
```

A user who chooses terminal setup can enter the Key in their own local `bash` session:

```bash
read -r -s -p "Video Transcriber API Key: " VS_API_KEY
export VS_API_KEY
printf '\n'
```

Then register and launch the client from that same environment. A terminal export does not update an already-running desktop app; a session variable is lost when the shell closes. Do not print the variable, expand it into command arguments, or claim that another Agent automatically inherits it.
