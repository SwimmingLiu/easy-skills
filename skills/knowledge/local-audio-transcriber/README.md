# Local Audio Transcriber

本地录音、音频和视频转文字 skill。

## 能做什么

- 把 `.mp3`、`.m4a`、`.wav`、`.mp4` 等已有音视频文件转成文字稿。
- 输出 `txt`、`md`、`json`、`srt`、`vtt`。
- Apple Silicon 机器优先使用 MLX 调用 Apple GPU。
- 非 Apple Silicon 机器继续使用 faster-whisper。

## 默认推荐

在 M1/M2/M3/M4 Mac 上，优先使用：

```bash
python3.13 -m venv /tmp/local-audio-transcriber-mlx
/tmp/local-audio-transcriber-mlx/bin/python -m pip install -U pip mlx-whisper
/tmp/local-audio-transcriber-mlx/bin/python scripts/transcribe.py input.mp3 --language zh --formats txt,md,json,srt,vtt
```

默认 MLX 模型是：

```text
mlx-community/whisper-large-v3-turbo-q4
```

它适合中文长录音、多人直播、专有名词较多的录音。首次运行会下载模型，后续复用本地缓存。

## 注意

- 默认本地处理，不上传音频。
- 长录音默认关闭 `condition_on_previous_text`，减少重复幻觉。
- 如果需要非常精确的逐字稿，仍建议人工抽听校对关键段落。
