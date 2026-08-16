# RightAPI Reference

## Configuration

Read these variables from the user's local `codex image gen key` section. Report only whether a
variable is set; never print its value.

| Variable | Purpose |
| --- | --- |
| `OPENAI_SUB_BASE_URL` | Drawing base URL, normally `https://www.rightapi.ai/draw` |
| `OPENAI_SUB_KEY` | Bearer credential |
| `OPENAI_SUB_IMAGE_MODEL` | Default image model |
| `OPENAI_SUB_IMAGE_VIP_MODEL` | Explicit VIP or higher-resolution model |

The skill does not create, rotate, or persist these values.

## Endpoints

RightAPI uses two different URL bases:

| Operation | URL |
| --- | --- |
| Submit | `POST https://www.rightapi.ai/draw/v1/images/generations` |
| Poll | `GET https://www.rightapi.ai/v1/tasks/{task_id}` |

The polling URL is site-level and does not contain `/draw`. Authenticate both requests with:

```text
Authorization: Bearer <local key>
```

The bundled client sends a curl-compatible User-Agent because some gateways reject the default
Python urllib signature.

## Submit Payload

Send JSON with `async` fixed to `true`:

```json
{
  "model": "gpt-image-2",
  "prompt": "A red apple on a white studio background",
  "n": 1,
  "size": "1:1",
  "async": true
}
```

Supported fields are `model`, `prompt`, `n`, `size`, `imageSize`, and `image`. `size` accepts
`1:1`, `16:9`, `9:16`, `4:3`, or a pixel string such as `1024x1024`. `imageSize` accepts `1K`,
`2K`, or `4K` when the selected model supports it.

Reference images use data URLs in an array:

```json
{
  "image": ["data:image/png;base64,<encoded image>"]
}
```

The submit response must contain a non-empty `task_id`:

```json
{
  "task_id": "task_<opaque id>"
}
```

## Polling

Poll until one of these states appears:

| State | Action |
| --- | --- |
| `queued`, `in_progress`, `processing` | Wait and poll again |
| `completed` | Read the image result |
| `failed`, `cancelled`, `canceled` | Stop and report `error.message` |

Some completed responses omit `status`. Treat the response as complete when it contains image
data. Supported result shapes include:

```json
{
  "status": "completed",
  "data": [{"url": "https://signed-result-url"}]
}
```

```json
{
  "data": [{"b64_json": "<base64 image>"}]
}
```

Do not print signed URLs. Download them immediately and report only the local output path.

## Troubleshooting

- `task_id` missing: stop before polling and report the sanitized response message.
- `403` during polling: verify the request uses the configured key and a curl-compatible
  User-Agent; do not rotate credentials or add a second provider automatically.
- TLS or connection error during polling: retry until `--poll-timeout`, then report the timeout.
- Completed response without `status`: inspect `data`, `images`, `output`, or `result`; the
  bundled adapter already treats image data as completion.
- No URL and no base64 result: report the task response shape without exposing signed URLs or
  credentials.

Official references:

- [RightAPI asynchronous workflow](https://docs.rightapi.ai/docs/rc_draw/#%E5%BC%82%E6%AD%A5%E6%B5%81%E7%A8%8B)
- [Image generations](https://docs.rightapi.ai/docs/rc_draw/images-generations.html)
- [Task polling](https://docs.rightapi.ai/docs/rc_draw/tasks.html)
