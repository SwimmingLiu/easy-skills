# AI 图片样例生成状态

当前 18 个规范主题的逐页草稿与提示词已经生成，见 `outline.json` 和 `imagegen-jobs.jsonl`。

18 条任务已通过 `$imagegen` 自带 `scripts/image_gen.py generate-batch --dry-run` 校验，模型、尺寸、输出文件名和提示词格式均可解析。

2026-08-03 实测结果：主生图通道、备用标准生图接口和 VIP 模型单页探测均返回 403，当前令牌无权使用配置模型；兼容服务也未提供可用的对话式生图接口。目录中没有放置占位图，也没有把其他来源图片冒充成本次生成结果。

修复本地模型权限后，在此目录运行：

```bash
export IMAGE_GEN="<imagegen-skill>/scripts/image_gen.py"
python "$IMAGE_GEN" generate-batch --input imagegen-jobs.jsonl --out-dir slides --concurrency 3
node ../../../../scripts/build-theme-showcases.mjs --assemble-ai
```

使用前请在本地为 `$imagegen` 配置具有 GPT Image 调用权限的 `OPENAI_API_KEY`。密钥只能通过环境变量或本机密钥配置提供，不能写进命令文件、提示词、日志或仓库。
