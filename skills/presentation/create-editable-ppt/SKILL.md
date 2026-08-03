---
name: create-bento-ppt
description: Use when a user asks for a PPT, presentation, slide deck, keynote, report, launch, defense, or wants source material turned into a concise themed deck that remains openable in Bento.
---

# Create Bento PPT

先读取 `references/workflow.md`。本 Skill 只提供两种互斥模式，不能在同一份演示中混用。

| 模式 | 页面由谁生成 | 可修改范围 | 适用场景 |
|---|---|---|---|
| `ai-image` | `imagegen` 生成一张完整的 16:9 页面图片 | 在 Bento 中替换整页图片、排序、删除、改备注；图片内文字不能单独修改 | 发布会、提案、品牌叙事，需要强视觉完成度 |
| `html` | Bento 原生文本、形状、SVG、图表和表格 | 元素级修改 | 汇报、答辩、培训、数据与流程说明 |

两种模式的主文件都是 `.bento.html`，文档格式为 `bento/slides`。不要另做一套自定义播放器，也不要把 Bento 仅当作设计参考。PNG、PDF 和 PPTX 都是派生文件；PPTX 为截图式导出，不承诺元素可编辑。

## 必经流程

1. **检查资料。** 明确受众、场景、语言、预计页数、交付格式和事实材料。资料缺失时列出缺口，不补造事实。
2. **先写草稿。** 生成 `outline_draft.json`，其中必须包含中心含义、五段叙事逻辑、预计页数，以及每页的角色、单页主张、准确文字、证据、视觉构思和转场。
3. **让用户确认。** 草稿未确认前，不得调用 `imagegen`，也不得生成最终页面。用户修改页数或某页主张时，只更新草稿。
4. **选择模式与主题。** 用 `themes --mode ai-image|html` 查看主题。主题目录来自完整来源库存，经版式语法、字体层级、材质和信息密度去重。
5. **生成。** `ai-image` 为每页生成一张完整图片；`html` 只写 Bento 原生元素，禁止调用生图、禁止使用整页栅格背景。
6. **差异化检查。** 逐页核对主张和准确文字。数据页检查来源、单位和量级；流程页检查顺序；对比页检查维度；图片页检查主体、裁切和文字；封面与结尾检查中心信息和行动指向。
7. **输出并复开。** 只替换 `<script type="application/bento+json" id="bento-doc">` 内的 JSON。复开 `.bento.html`，确认页数、主题、备注、资产和稳定 ID 完整。

## 命令

在本 Skill 目录运行：

```bash
node scripts/ppt.mjs draft <project-dir> --title "标题"
node scripts/ppt.mjs themes --mode ai-image
node scripts/ppt.mjs approve <project-dir> --mode ai-image --theme editorial-ink
node scripts/ppt.mjs prompts <project-dir>
# ai-image：按 imagegen-jobs.jsonl 生成图片后继续
node scripts/ppt.mjs build <project-dir>
node scripts/ppt.mjs qa <project-dir> --json
```

`html` 模式在 `approve` 后可直接 `build`。`ai-image` 模式缺少任何页面图片时必须停止，不得用占位图假装完成。

`--theme` 既接受规范主题 ID，也接受库存中的来源别名。例如 `open-slide:minecraft` 会解析为 `pixel-arcade`；审批文件同时保留规范 ID 和原始别名。

## Imagegen

`ai-image` 模式必须使用 `$imagegen`。优先使用宿主内置生图能力；只有用户明确选择 CLI/API 路径时才使用 CLI。若使用 CLI，提醒用户在本地设置 `OPENAI_API_KEY`，不要要求用户在对话中粘贴密钥，也不要把密钥写入提示词、日志或项目文件。

每个提示词必须包含页面角色、单页主张、准确文字、主题配方、视觉构思和禁止项。准确文字是封闭列表，不得增加虚构数字、引用、品牌、标签或水印。生图失败时只重试失败页，并保留失败记录。

## Bento 文档约束

- `#bento-doc` 是唯一数据源，必须是明文 JSON，`format` 必须为 `bento/slides`。
- 嵌入 JSON 前把 `<` 转义为 `\u003c`，防止 `</script>` 提前结束脚本。
- 编辑现有文档时保留 `docId`、未知字段和稳定的 slide/element ID。
- `ai-image` 每页只有一个全画布 `image` 元素；`html` 不得出现全页图片元素。
- `ai-image` 只接受可识别的 PNG/JPEG，且宽高比必须为 16:9；比例错误或文件损坏时拒绝组装。
- 每页写 speaker notes，记录页面目的、主张和必要的证据说明。

## 异常与兜底

- 上传文件缺失或不可读：列出路径，继续读取可用资料，把受影响页面标记为未解决。
- 资料不足以支撑预计页数：建议缩短页数，并指出哪些页面需要补证据。
- `ai-image` 缺少可用视觉构思或必要的事实图片：停在准备状态，不生成虚构截图、图表或产品结果。
- 生图配置缺失：提示用户在本地配置相关密钥；`html` 模式不受影响。
- 页面文字错误、构图偏离或主题漂移：只回退该页，修正草稿或提示词后重做。
- Bento 壳缺失、存在多个 `#bento-doc`、文档格式错误或 `docId` 被改变：拒绝写入。

## 参考文件

- `references/workflow.md`：输入、草稿确认、生成、检查和回退。
- `references/image-theme-inventory.json`：图片主题完整来源库存。
- `references/html-theme-inventory.json`：HTML 主题完整来源库存。
- `assets/themes/theme-catalog.json`：去重后的 18 个图片主题和 22 个 HTML 主题。
- `assets/bento/SOURCE.json`：Bento 壳的来源、提交与校验值。
- `assets/examples/bento-theme-showcase/html/theme-showcase.bento.html`：22 个 HTML 主题的可编辑样例。
- `assets/examples/bento-theme-showcase/html/qa/contact-sheet.png`：22 个 HTML 主题总览。
- `assets/examples/bento-theme-showcase/ai-image/GENERATION_STATUS.md`：18 个 AI 图片主题样例的生成状态与执行方法。
