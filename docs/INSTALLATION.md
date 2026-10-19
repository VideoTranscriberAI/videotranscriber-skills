# Advanced installation

For the recommended plugin installation and natural-language first run, start with the [English README](../README.md) or [中文说明](../README_zh.md). The plugin installs all three Skills. Installing Skills does not supply an API Key.

## Agent Skills CLI

For agents supported by the Skills CLI:

```bash
npx skills add VideoTranscriberAI/videotranscriber-skills
```

Select `setup-videotranscriber`, `transcribe-media`, and `transcript-insights` and the intended agent. A standalone business Skill remains usable when the setup Skill is absent, with the documented manual connection fallback.

## Codex CLI — standalone Skills

```bash
git clone https://github.com/VideoTranscriberAI/videotranscriber-skills.git
mkdir -p ~/.agents/skills
cp -R videotranscriber-skills/skills/setup-videotranscriber ~/.agents/skills/
cp -R videotranscriber-skills/skills/transcribe-media ~/.agents/skills/
cp -R videotranscriber-skills/skills/transcript-insights ~/.agents/skills/
```

Check for existing Skill directories before copying; preserve local modifications and avoid installing a duplicate plugin/standalone copy. Start a new conversation if discovery does not refresh.

## Claude Code — standalone Skills

Use the same repository clone, then:

```bash
mkdir -p ~/.claude/skills
cp -R videotranscriber-skills/skills/setup-videotranscriber ~/.claude/skills/
cp -R videotranscriber-skills/skills/transcribe-media ~/.claude/skills/
cp -R videotranscriber-skills/skills/transcript-insights ~/.claude/skills/
```

Standalone installation does not load the Claude plugin's bundled MCP or credential form. Use the [client connection steps](../skills/setup-videotranscriber/references/clients.md).

## Project installation

Copy a selected Skill directory under the host's project Skills path, such as `.agents/skills/` for Codex or `.claude/skills/` for Claude Code. Keep credentials out of the project and version control. User-wide plugin installation is the recommended beginner route.

## Explicit invocation

Natural-language requests are supported. These forms are useful when multiple installed Skills overlap:

```text
Use $setup-videotranscriber to connect Video Transcriber and check the connection.
Use $transcribe-media to transcribe a public media URL.
Use $transcript-insights to summarize the attached subtitles.
```

Claude Code plugin:

```text
/videotranscriber-skills:setup-videotranscriber
/videotranscriber-skills:transcribe-media
/videotranscriber-skills:transcript-insights
```

Standalone Claude Skills use `/setup-videotranscriber`, `/transcribe-media`, and `/transcript-insights`.

## Packaging and connection formats

- `.codex-plugin/plugin.json`: Codex plugin metadata and canonical Skills. Use setup to configure the client-owned MCP connection and credential.
- `.claude-plugin/plugin.json`: canonical Skills plus a plugin MCP entry referencing a sensitive `userConfig.api_key` value. No real credential is bundled.
- [WorkBuddy packages](WORKBUDDY.md): per-skill upload ZIPs and a Token connector adapter built from canonical sources.

The endpoint accepts a Bearer API Key and does not provide OAuth. A repo marketplace installation is not a public directory listing. These instructions cover the local Codex/plugin connection route; do not assume identical credential UI in every ChatGPT surface. [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins) describes the host-specific distribution options.
