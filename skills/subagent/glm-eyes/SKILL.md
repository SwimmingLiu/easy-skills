---
name: glm-eyes
description: 当主模型（如 GLM-5.2）无法读取图片时，用 sub-agent 调起任意多模态 Claude provider 来理解图片并返回文字描述。模型无关：不写死 Kimi，自动在 CC-Switch 路由中找一个已知的视觉模型，也可显式指定 provider。触发场景："图片读不了 / image read failed / 需要看图但当前模型不支持视觉 / 用 kimi 看图 / 用 glm-eyes 读图 / 描述这张截图 / 识别这张图片"。
license: MIT
metadata:
  version: 1.0.0
  domains: [vision, multimodal, fallback, model-orchestration]
  type: system
---

# glm-eyes — GLM 看不见？换双眼睛

## 何时使用此技能

当**当前主模型无法读取图片**时使用。典型场景：

- 当前 CC-Switch 路由是 GLM-5.2 等纯文本模型，对图片"看不见 / 看不清"；
- 用户上传或引用了一张图，要求描述、OCR、还原 UI、提取图表数据；
- 触发词："图片读不了 / image read failed / 看不了一张图 / 用 kimi 看图 / 用 glm-eyes 读图 / 描述这张截图"。

## 工作原理（模型无关）

1. 你的 CC-Switch 里配置了多个 Claude provider，其中一些对应真实的多模态模型（例如 `Kimi-flik` 的 `kimi-for-coding[1M]`）。
2. 本技能**不切** CC-Switch 全局路由（会打断当前 GLM-5.2 会话），而是让 sub-agent 直接调用某个多模态 provider 的 Anthropic 兼容 `/v1/messages` 接口。
3. 脚本自动挑选 provider：先看当前激活路由是否本身就是多模态；若不是，就在所有 Claude provider 里按模型名匹配"已知视觉模型清单"。
4. 凭据从 `~/.cc-switch/cc-switch.db` 实时读取，不落盘到代码里。

## 调用方式

主对话发现自己读不了图后，spawn 一个 sub-agent 执行脚本并返回 stdout：

```bash
# 自动挑选多模态 provider
python3 ~/.claude/skills/glm-eyes/scripts/glm_eyes.py "<图片绝对路径>" "<prompt>"

# 显式指定 CC-Switch 里的某个 provider
python3 ~/.claude/skills/glm-eyes/scripts/glm_eyes.py "<图片绝对路径>" "<prompt>" --provider Kimi-flik
```

推荐 sub-agent 调用模板：

```
Agent(subagent_type="general-purpose",
      prompt="运行命令 `python3 ~/.claude/skills/glm-eyes/scripts/glm_eyes.py '<图片路径>' '<prompt>'`，"
             "并把 stdout 中的图片描述原样返回，不要改写。")
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `image` | 是 | 本地图片绝对路径，支持 png/jpg/jpeg/gif/webp/bmp，≤20MB |
| `prompt` | 否 | 你想让视觉模型关注什么。默认会详细描述 UI/图表/场景 |
| `--provider NAME` | 否 | 强制使用 CC-Switch 中名为 `NAME` 的 Claude provider |
| `--max-tokens N` | 否 | 最大输出 token，默认 4096 |

## Provider 选择与 fallback

**显式指定**（`--provider NAME` 或环境变量 `GLM_EYES_PROVIDER`）：只使用该 provider。若其模型未命中多模态清单，脚本会**立即拒绝**（exit 2，不发请求），避免拿纯文字模型去调图像接口空耗。

**自动模式**（默认）：按优先级构造候选列表，**依次尝试直到成功**：

1. CC-Switch 当前激活路由（若多模态）
2. 其余命中多模态清单的 Claude provider
3. 环境变量 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` 兜底

某个候选 503 / 网络错 / 鉴权失败时，stderr 打 WARN 并自动试下一个；只有全部失败才 exit 2 并列出每条错误。这样即使某个代理账号当下没额度，技能也能自动靠另一个视觉模型把图读完。

## 已知多模态模型清单（自动探测）

脚本通过模型名中的关键字判断（小写匹配）：

- `kimi` (kimi-for-coding)
- `claude` (Claude 官方 / 兼容代理，3/4 系均支持视觉)
- `gpt-4o`, `gpt-5`, `chatgpt`
- `qwen-vl`, `qwen2-vl`, `qwen2.5-vl`, `qwen3-vl`
- `glm-4v`, `glm-v`
- `gemini`
- `llava`, `vision`, `vl`

> 注意：`glm-5.2` 裸文字模型不含 `v` / `vision` / `vl`，因此不会被误判为多模态。

## 给新模型加支持

只要你的 CC-Switch provider 满足下面两点，脚本就能用：

1. **走 Anthropic 兼容协议**（因为所有 CC-Switch "Claude" provider 都按 Anthropic API 配置）；
2. **模型名命中上述关键字**；若没命中，可用 `--provider` 或 `GLM_EYES_PROVIDER` 强制指定。

如果未来某个视觉模型的名字完全不在清单里，编辑 `scripts/glm_eyes.py` 的 `VISION_MODEL_HINTS` 元组即可。

## 退出码 / 错误

| 退出码 | 含义 |
|------|------|
| 0 | 成功，图像描述在 stdout |
| 1 | 参数错误 / 文件不存在 / 图片过大 |
| 2 | 找不到可用多模态 provider / 接口调用失败（鉴权/网络/5xx/无文本返回） |

错误信息走 stderr，不污染主对话拿到的 stdout。

## 注意事项

- 当前 GLM-5.2 路由若切换到别的模型（例如 GLM-4V），当前激活路由会直接命中 `glm-v` / `vision` 关键字，本技能会自动使用当前路由，无需指定 `--provider`。
- 脚本只会读取 CC-Switch db，不会修改任何 provider 配置或切换路由。
- 一次调用读一张图；多张图请循环 spawn 多个 sub-agent。