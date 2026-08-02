# 素材与生图协议

## 槽位优先

先在页表定义图片用途、主体、比例、是否承载事实，再决定来源。没有槽位就不生成装饰图。

素材优先级：用户原图、可追溯公开素材、真实数据生成的图表、AI 示意图、明确占位。

## 宿主生图

核心运行时不绑定 ChatGPT、Chat Image、gpt-image-2、Image Two 或其他供应商。调用当前宿主可用的图片生成能力，并以 manifest 保存实际 prompt、模型和输出文件。当前 CLI 任务由 `prompts` 写入 `imagegen-jobs.jsonl`：`image-first` 的 PNG 放入 `slides/`，`html-image-assisted` 的背景板/插图放入 `assets/`。

整页图片必须 `fact_bearing: false`，除非文字和数字来自用户确认的 exact text 或受控素材。避免图内长文字、Logo、真实数据、真实产品截图和论文结果。`image-first` 的文字必须先进入内容草稿并原样传给模型；`html-image-assisted` 的视觉提示词不得包含文字清单，所有需要呈现的文字由 HTML 从内容草稿读取。

若宿主没有内置生图能力，而用户明确选择 CLI/API 模式，先执行 `node scripts/ppt.mjs doctor --json`。当 `imagegen.cli_key_configured` 为 `false` 时，提示用户在本机设置标准 `OPENAI_API_KEY`，或 imagegen 约定的 `OPENAI_SUB_*` 主配置 / `OPENAI_SUB_FALLBAK_*` 备用配置后再继续；不要要求用户在聊天中发送密钥。密钥缺失时可使用有明确来源和授权的图片，或保留可替换图片槽，不得静默切换模型。

## 来源与授权

每项素材记录 SHA-256、原始文件名、用途、来源、授权、尺寸和替代文本。搜索素材与生成素材缺少授权信息会产生 warning；不能确认使用权时在最终交付前替换。
