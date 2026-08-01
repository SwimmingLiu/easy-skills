# Image-first PPT 实施审计

审计对象：`skills/presentation/create-editable-ppt/`。

## Bento 思路的落地

| Bento 关键思想 | 本 Skill 的实现 |
|---|---|
| JSON 是 source of truth | `outline_draft.json` -> `deck_spec.json` -> `generation_manifest.json`；生成后的 HTML 不反推内容 |
| 单文件、离线优先 | `ppt.mjs bundle` 生成 `dist/presentation.image-ppt.html`，以 `image-ppt-doc` JSON block 保存文档 |
| 资产内嵌 | bundle 把每张 PNG 写成 `data:` URI，不依赖远程 URL 或项目相对路径 |
| 一个渲染器服务多个视图 | `renderImageDeck` 服务本地播放，bundle runtime 服务离线播放；同一 manifest 驱动画廊、PPTX 与 QA |
| 稳定 ID 与连续性 | 每页保留 `id`、`visual_anchor_id`、`continuity_group`、`transition`，保证整页重生时叙事锚点不漂移 |
| AI round-trip | AI/宿主修改草稿、JSON 或 manifest 后只重生受影响页面，不编辑生成 HTML |

参考：[Bento README](https://github.com/SwimmingLiu/bento)。本项目借鉴其文档模型与离线封装方式，没有复制代码或运行时。

## 设计到代码的对应关系

| 设计要求 | 证据 | 状态 |
|---|---|---|
| 中心含义、叙事逻辑和逐页主张确认 | `outline_draft.json`、`outline_preview.html`、`approveOutlineDraft()` | 完成 |
| 整页图片优先 | `compileSlidePrompt()`、`renderImageDeck()`、`output_mode: full-slide-image` | 完成 |
| 八个去重主题 | `assets/themes/image-themes.json` | 完成 |
| imagegen 接口与本地密钥提醒 | `imagegen-jobs.jsonl`、`doctor`、`references/assets.md` | 完成 |
| 缺资料、缺图、失败和主题漂移兜底 | `SKILL.md`、`references/workflow.md`、manifest 状态 | 完成 |
| 差异化 Review | `SKILL.md`、`references/qa-export.md`、`qa` | 完成 |
| 可替换但不伪造的样例回退 | `imagegen-fallback-notice.md`、`source_kind` | 完成 |
| 桌面/移动画廊与翻页检查 | `verify-image-showcase.mjs`、`gallery-qa.json` | 完成 |

## 样例验证

- 样例内容：`AI 原生知识工作流`，中心含义为“让散落的信息和判断沿着工作流持续产生价值”。
- 主题：8 个；每个主题 3 页（cover / process / closing）；合计 24 页。
- 内容 QA：8/8 主题 `export_ready: true`，0 blocking。
- 浏览器 QA：24 张图片全部加载，8 个主题均可翻页，桌面和移动画廊无横向溢出，0 blocking。
- imagegen 状态：本次 CLI 请求因外部账户无 active plan 而失败；样例 PNG 使用已有本地主题截图作为明确标注的 fallback，不冒充新生成结果。
