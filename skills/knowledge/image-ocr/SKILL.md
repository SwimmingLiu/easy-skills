---
name: image-ocr
description: 识别图片、截图、照片、扫描件和图片型 PDF 中的文字。用户要求 OCR、提取图中文字、截图转文字、批量识别图片，或需要保留表格、公式、多栏版面等文档结构时使用；普通可复制文本的读取不使用此技能。
---

# Image OCR

从用户提供的本地图片或 PDF 中提取文字。默认先用 RapidOCR 做快速、离线的中英文识别；只在结果不可靠时用当前模型的图片理解能力兜底；复杂文档使用 PaddleOCR PP-StructureV3。

## 路由

- 普通截图、照片、单栏扫描件：使用 RapidOCR。
- PDF、表格、公式、多栏排版、印章、图文混排，或用户明确要求保留结构：使用 PaddleOCR。
- RapidOCR 输出的 JSON 中 `needs_vision_fallback` 为 `true`、没有识别出文字、引擎报错或格式不受支持：查看原图并用模型视觉重新识别。
- PaddleOCR 失败时，可以用模型视觉提取可见文字，但要明确说明版面、表格或公式结构可能不完整，不能把视觉结果冒充结构化解析结果。

## 执行

先确认附件对应的本地文件路径。不要把图片上传到第三方 OCR 服务。

首次使用 RapidOCR 时，在独立环境中安装依赖，不污染系统 Python：

```bash
uv venv ~/.cache/image-ocr/venv --python 3.13
uv pip install --python ~/.cache/image-ocr/venv/bin/python rapidocr onnxruntime
```

普通图片识别：

```bash
~/.cache/image-ocr/venv/bin/python {skill_dir}/scripts/ocr.py "input.png" \
  --engine rapid --output-dir ./ocr-output --formats txt,json --print-text
```

复杂文档识别：

```bash
~/.cache/image-ocr/venv/bin/python {skill_dir}/scripts/ocr.py "document.pdf" \
  --engine paddle --output-dir ./ocr-output --formats md,txt,json --print-text
```

多张普通图片可以一次传入。`--engine auto` 对 PDF 使用 PaddleOCR、对其他输入使用 RapidOCR；它不会根据图片内容自动判断复杂版式，因此已知是表格、多栏或公式时要显式指定 `--engine paddle`。

安装 PaddleOCR、调整阈值或排查引擎问题时，读取 [references/engines.md](references/engines.md)。

## 模型视觉兜底

1. 读取 RapidOCR 生成的 `.ocr.json`，检查 `fallback_reasons` 和低置信度文本行。
2. 使用可用的本地图片查看工具打开原图；PDF 先渲染相关页面再查看。
3. 按原始阅读顺序逐字提取。看不清的字符标为 `[无法辨认]`，不要猜测。
4. 对照 RapidOCR 结果修正明显漏行和错字。用户只要求“提取原文”时不要擅自润色；如需整理，同时保留原始识别文本和整理稿。

模型视觉是 Skill 的编排步骤，不是 `ocr.py` 内部的网络调用。脚本只负责本地 OCR，并用 `needs_vision_fallback` 告知调用者是否需要兜底。

## 交付

- 在回复中直接给出识别正文；长文本同时提供生成文件。
- 普通图片至少保留 `.ocr.txt` 和 `.ocr.json`；复杂文档优先交付 `.ocr.md` 和 `.ocr.json`。
- 多图批处理时说明各文件是否成功、使用的引擎，以及哪些文件经过模型视觉兜底。
- 对低置信度内容保留不确定性，不要用语言模型悄悄改成“看起来合理”的文字。
