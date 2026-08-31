# OCR 引擎说明

仅在安装依赖、选择复杂文档参数、解释输出 JSON 或排查失败时读取本文件。

## 运行环境

推荐使用独立的 Python 3.13 环境：

```bash
uv venv ~/.cache/image-ocr/venv --python 3.13
```

RapidOCR 默认依赖：

```bash
uv pip install --python ~/.cache/image-ocr/venv/bin/python rapidocr onnxruntime
```

PP-StructureV3 需要 PaddleOCR 的文档解析依赖组和一个推理引擎：

```bash
uv pip install --python ~/.cache/image-ocr/venv/bin/python "paddleocr[doc-parser]"
uv pip install --python ~/.cache/image-ocr/venv/bin/python paddlepaddle
```

Apple Silicon 上如果 PyPI 没有匹配的 PaddlePaddle wheel，使用官方 CPU 索引安装：

```bash
uv pip install --python ~/.cache/image-ocr/venv/bin/python \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ paddlepaddle
```

PaddleOCR 和模型首次运行会下载较大的模型文件，之后使用本地缓存。脚本把 PaddleX 模型缓存设为 `~/.cache/image-ocr/paddlex`。不要在用户未要求复杂结构时提前安装或加载 PaddleOCR。

## 引擎选择

### RapidOCR

适合截图、照片、海报、单栏扫描页和批量小图。默认中英文模型，返回文本行、坐标框、置信度和耗时。

```bash
python scripts/ocr.py a.png b.jpg --engine rapid --formats txt,json
```

以下任一条件会令 `needs_vision_fallback=true`：

- 没有识别到非空文本；
- 平均置信度低于 `--fallback-threshold`，默认 `0.72`；
- 任一文本行置信度低于 `--line-threshold`，默认 `0.45`。

阈值只决定是否建议模型视觉复核，不会删除低置信度文本。

### PaddleOCR PP-StructureV3

适合 PDF、表格、公式、多栏、印章、图文混排和需要 Markdown 结构的文档。默认开启文档方向识别、图像矫正和文本行方向识别。

```bash
python scripts/ocr.py document.pdf --engine paddle --formats md,txt,json
```

常用参数：

- `--language en`：英文文档；不传时使用默认中英文配置。
- `--device cpu`：显式使用 CPU；也可以按 PaddleOCR 支持的格式传入 GPU 设备。
- `--paddle-engine paddle`：默认本地 Paddle 推理后端。
- `--disable-formula`：不需要公式识别时减少模型负担。
- `--disable-table`：不需要表格结构时关闭表格模块。
- `--disable-seal`：不需要印章文字时关闭印章模块。
- `--no-unwarp`：输入已经平整时关闭文档矫正。

如果当前 PaddleOCR 版本的后端参数发生变化，先运行 `python scripts/ocr.py --help`，再对照已安装版本的 PP-StructureV3 官方文档；不要静默改用云端 PaddleOCR API。

## 输出

每个输入使用稳定的文件名：

- `<name>.ocr.txt`：按阅读顺序合并的纯文本；
- `<name>.ocr.md`：Markdown，复杂文档优先使用；
- `<name>.ocr.json`：机器可读结果。

JSON 关键字段：

```json
{
  "schema_version": 1,
  "status": "ok",
  "source": "/absolute/path/input.png",
  "engine": "rapidocr",
  "text": "识别正文",
  "average_confidence": 0.96,
  "needs_vision_fallback": false,
  "fallback_reasons": [],
  "lines": [
    {
      "text": "识别正文",
      "confidence": 0.96,
      "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]
    }
  ],
  "artifacts": {
    "txt": "/absolute/path/input.ocr.txt",
    "json": "/absolute/path/input.ocr.json"
  }
}
```

PaddleOCR 的 `average_confidence` 为 `null`，结构化页面内容位于 `pages`，合并后的 Markdown 位于 `markdown`。

## 常见失败

- `rapidocr is not installed`：在独立环境安装 `rapidocr onnxruntime`。
- `paddleocr document parser is not installed`：安装 `paddleocr[doc-parser]` 和推理后端。
- Python 3.14 找不到 PaddlePaddle wheel：改用 Python 3.13 虚拟环境。
- PDF 被 RapidOCR 拒绝：改用 `--engine paddle`，或先将页面渲染成 PNG 后逐页使用 RapidOCR。
- HEIC、损坏图片或超大图片解码失败：先无损转为 PNG，再识别；仍失败则使用模型视觉。
- PaddleOCR 初始化或模型下载失败：保留错误信息并报告，不要把模型视觉结果称为 PP-StructureV3 结果。
