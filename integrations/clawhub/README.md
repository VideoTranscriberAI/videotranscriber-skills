# Video Transcriber AI for OpenClaw

Connect [Video Transcriber AI](https://videotranscriber.ai/) to OpenClaw using your own API Key. This bundle includes connection guidance, public-media transcription, and transcript analysis.

## Start

1. Install the bundle from its ClawHub listing or a reviewed local bundle directory.
2. Sign in to Video Transcriber AI and create a Key in the API console.
3. Complete both required bindings on the Gateway/profile that runs this plugin: supply `VS_API_KEY` to its environment and explicitly configure the same-name native `mcp.servers.videotranscriber` connection with `Authorization: Bearer ${VS_API_KEY}`. Follow the [OpenClaw connection guide](skills/setup-videotranscriber/references/openclaw.md) for the exact non-secret configuration and local, service, remote, and named-profile setup. Apply it to the Gateway before checking the connection. Never paste a Key into chat or include it in a command argument.
4. Ask: **Help me connect Video Transcriber AI and check the connection.** The check discovers tools without creating a transcription.
5. Provide a supported public media URL and the requested transcript, subtitles, summary, or learning notes.

Transcription uses independent API Quota. Website credits and unlimited website plans do not cover API calls. Basic transcription is the default; advanced options, API chapters, and API translation consume additional quota when selected. The service's actual usage is authoritative.

## Included Skills

| Skill | Purpose |
| --- | --- |
| `setup-videotranscriber` | Configure and verify the connection, then continue the original request. |
| `transcribe-media` | Create a transcription, poll within a bounded budget, and retrieve results. |
| `transcript-insights` | Analyze supplied or retrieved transcripts and subtitles. |

Pasted transcripts and SRT/VTT analysis require no Video Transcriber credential and make no transcription API call. If the unconfigured MCP connection reports an unavailable credential, continue text analysis with `transcript-insights`; do not create a paid task as a test.

## Connection and recovery

The service is `https://videotranscriber.ai/mcp`, using Streamable HTTP and a Bearer API Key. The bundle contains only `${VS_API_KEY}`, never a credential. The explicit native Gateway connection is required so its configuration loader expands the reference; installing the bundle and supplying the environment variable alone do not complete setup. OpenClaw's Gateway must receive the value; setting a variable in an unrelated terminal does not configure a running service. Preserve other servers and reuse `videotranscriber` so the native entry overrides the bundle without creating a duplicate connection.

Reuse existing task IDs and creation idempotency keys. Connection failures, expired results, and failed tasks do not authorize creating replacements. See the [tool contract](skills/transcribe-media/references/tool-contract.md) for arguments and error decisions. Local/private media uploads are not supported.

## Privacy and license

Transcription sends your public media URL and selected options to Video Transcriber AI. Transcript analysis uses your host agent and its data policy. Do not publish credentials, private transcripts, or signed result URLs. See [privacy](https://videotranscriber.ai/privacy), [terms](https://videotranscriber.ai/terms), and the included [MIT License](LICENSE).
