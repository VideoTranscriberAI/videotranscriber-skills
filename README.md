# Video Transcriber AI Skills

Official Skills from [Video Transcriber AI](https://videotranscriber.ai/) — connect your AI client, transcribe public media, and turn transcripts into useful notes.

[![Validate Skills](https://github.com/VideoTranscriberAI/videotranscriber-skills/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/VideoTranscriberAI/videotranscriber-skills/actions/workflows/validate-skills.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) | [简体中文](README_zh.md)

## Start here

1. Install using the instructions for your client below.
2. Say **“Help me connect Video Transcriber.”** The setup Skill guides credential entry and checks the connection.
3. Send a public media link and say what you want: a transcript, subtitles, summary, or learning notes.

**Transcription uses independent API Quota. Website credits and unlimited website plans do not cover API calls.** Create a Key in the API console after signing in to [Video Transcriber AI](https://videotranscriber.ai/). Paste it once into the hidden local input or client credential settings, never in chat. Existing transcript/subtitle analysis does not require an API Key or consume Video Transcriber API Quota; the host's own model usage follows its pricing.

## Install for your client

### ChatGPT Desktop with Codex / Codex CLI

Run in a local terminal:

```bash
codex plugin marketplace add VideoTranscriberAI/videotranscriber-skills
codex plugin add videotranscriber-skills@video-transcriber-ai
```

In the desktop app you can install from **Plugins Directory → Video Transcriber AI → Video Transcriber AI Skills** after adding the marketplace. Open a new conversation and ask to connect.

The setup Skill launches a local helper. Paste the Key once into its hidden input; it validates and saves the connection, then checks the current tools and resumes your request. If native MCP tools have not loaded, the packaged MCP caller continues the task in the same conversation using the saved Key. Temporary verification failures are retried in the same process without another paste; installed curl is preferred for HTTP requests. The Key is saved as plaintext in your local user config with restricted file permissions and remains available after restart. The helper requires Python 3.11+; if a local window cannot open, it provides a hidden-input command for your own terminal. See [local setup](skills/setup-videotranscriber/references/local-setup.md). Plugin installation does not supply a Key. These instructions target the local Codex/plugin route; other ChatGPT surfaces have their own connection requirements.

### Claude Code

Run inside Claude Code:

```text
/plugin marketplace add VideoTranscriberAI/videotranscriber-skills
/plugin install videotranscriber-skills@video-transcriber-ai
```

Enable the plugin and ask to connect Video Transcriber. Use the native **Video Transcriber API Key** field if your client presents it; otherwise the setup Skill launches the same [local helper](skills/setup-videotranscriber/references/local-setup.md), writes the Claude Code user configuration, and continues through native tools or the packaged MCP caller without requiring a client restart. Existing-text analysis requires no Key. Environment-based options remain in the [client-specific guide](skills/setup-videotranscriber/references/clients.md).

### WorkBuddy

Use the **Skills → Add Skill → Upload Skill** route for the per-skill ZIP packages. Then ask to connect; the setup Skill opens the local private input and saves the WorkBuddy user MCP configuration. See [WorkBuddy installation and packaging](docs/WORKBUDDY.md).

The repository also includes a Token connector adapter with a local Key form. Marketplace distribution requires WorkBuddy review; this repository does not imply an existing market listing. Target-client behavior still needs installation testing.

### Cursor, Windsurf, Gemini CLI, Copilot, VS Code, Cline, and Roo Code

Install the three standard Skills using your client's supported Skill installer, or ask the Agent to install this repository. For clients supported by the Skills CLI, see [advanced installation](docs/INSTALLATION.md). Then describe the video task normally or say “Help me connect Video Transcriber.”

The setup Skill uses one local configuration helper with a client-specific adapter. Paste the Key once into the private local window; the helper verifies it and saves only that client's user configuration. For a custom editor profile, the Agent first locates its active user MCP configuration. The client must allow local script execution; a native credential form or hidden terminal input is the fallback.

Configuration formats have automated test coverage. Actual Skill discovery, credential UI, and connection reload behavior need acceptance in each installed client. See [supported clients and paths](skills/setup-videotranscriber/references/local-setup.md) and the [client acceptance checklist](docs/CLIENT_TESTING.md).

## Just ask naturally

```text
Help me connect Video Transcriber and check the connection.
```

```text
Transcribe this video, then summarize it as learning notes: https://www.youtube.com/watch?v=e8WaTlzuid0
```

The second example uses the official product video and creates a real task that consumes API Quota. It is not a connection check.

```text
Check the previous transcription again.
```

```text
Summarize the attached subtitles and extract action items.
```

You do not need to memorize Skill names or invoke the transcription and analysis Skills separately. Pending tasks are resumed with their original ID rather than recreated.

## Try without an API Key

Paste the following fictional subtitles and ask “Summarize these subtitles”:

```srt
1
00:00:00,000 --> 00:00:04,000
Today we compared two onboarding screens.

2
00:00:04,000 --> 00:00:09,000
We chose the shorter screen. Mei will prepare the draft by Friday.
```

This exercises transcript analysis without calling the transcription service. An [official product-video subtitle example](examples/transcript-insights/official-video-subtitles.srt) and [expected output](examples/transcript-insights/official-video-expected-output.md) are also included.

## Included Skills

| Skill | What it does |
| --- | --- |
| `setup-videotranscriber` | Guides connection, credential entry, non-billable discovery checks, and recovery. |
| `transcribe-media` | Transcribes public media, retrieves SRT/VTT, resumes tasks, and hands the text to analysis. |
| `transcript-insights` | Produces requested summaries, insights, actions, open questions, translations, chapters, decisions, learning notes, and mind maps. |

If no analysis output is specified, transcript-insights returns Executive Summary, Key Insights, Action Items, and Open Questions. It matches the user's language and preserves source evidence.

## Inputs and limits

- Transcription accepts supported public HTTP/HTTPS media URLs and existing task IDs. Local/private media upload is not supported by these MCP tools.
- Text analysis accepts pasted content or accessible TXT, Markdown, SRT, VTT, and recognizable transcript JSON files.
- Basic transcription is the default. Advanced models and paid chapters/translation are used only when requested; summarizing a video does not silently enable those API features.
- Failed tasks are not automatically recreated. Unknown facts, owners, dates, and timestamps are not invented.

## Connection help

The service endpoint is `https://videotranscriber.ai/mcp`, authenticated with a Bearer API Key. Read the [official MCP overview](https://videotranscriber.ai/code-docs#mcp-overview) or [client-specific connection steps](skills/setup-videotranscriber/references/clients.md).

Installing Skills and authenticating the connection are separate operations; setup guides both. A saved setting alone is not proof of a working connection. Connection checks do not create transcription tasks or verify sufficient quota.

For terminal/manual Skill installation and explicit Skill invocation, see [advanced installation](docs/INSTALLATION.md). Architecture and contribution details: [architecture](docs/ARCHITECTURE.md), [contributing](CONTRIBUTING.md), [roadmap](ROADMAP.md), [release notes](RELEASE_NOTES.md).

## Privacy and license

Transcription sends the supplied media URL and selected options to Video Transcriber AI. Transcript analysis runs in the host agent environment, subject to its configuration and data policy. Do not commit private transcripts, credentials, or signed result URLs. See [product privacy](https://videotranscriber.ai/privacy).

Licensed under the [MIT License](LICENSE).
