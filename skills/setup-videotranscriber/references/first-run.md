# First-run examples

## Try analysis without a connection

When the user asks to try a demo, pass this fictional subtitle text to `transcript-insights` and return a brief summary in the user's language:

```srt
1
00:00:00,000 --> 00:00:04,000
Today we compared two onboarding screens.

2
00:00:04,000 --> 00:00:09,000
We chose the shorter screen. Mei will prepare the draft by Friday.
```

Expected: the summary reflects the shorter onboarding screen. If action items are requested, Mei prepares the draft by Friday; no calendar date is inferred. This does not call the transcription service or consume Video Transcriber API Quota. The host's own model usage still follows its pricing.

## First transcription after connecting

Offer this public official product video only when the user wants to try transcription:

```text
帮我转写这个视频，并整理成中文学习笔记：https://www.youtube.com/watch?v=e8WaTlzuid0
```

This is a real transcription request and uses API Quota. It is not a free connection check. Do not submit it merely because setup succeeded. Explain URL accessibility errors without substituting a fictional transcript.

## Useful recovery language

- Missing connection: “还需要连接 Video Transcriber。我会按你正在用的客户端引导配置。”
- Invalid Key: “连接凭证未通过验证，请在客户端的 API Key 配置处替换；不用发到聊天里。”
- Missing quota: “这次转写使用独立的 API 额度，网站会员积分不能抵扣。请到 API 控制台查看余额。”
- Pending task: “转写仍在处理中。在当前对话发送‘继续查看刚才的转写’即可查询同一个任务。” Keep the task ID available for resuming in another chat.
