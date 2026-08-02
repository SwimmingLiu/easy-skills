# AI 图片样例生成状态

当前 18 个规范主题的逐页草稿与提示词已经生成，见 `outline.json` 和 `imagegen-jobs.jsonl`。

2026-08-03 实测结果：主生图通道返回 403（当前令牌无权使用配置模型），备用通道返回请求被拦截；VIP 模型单页探测结果相同。目录中没有放置占位图，也没有把其他来源图片冒充成本次生成结果。

修复本地模型权限后，在此目录运行：

```bash
imagegen-cli generate-batch --input imagegen-jobs.jsonl --out-dir slides --concurrency 3
node ../../../../scripts/build-theme-showcases.mjs --assemble-ai
```

密钥应通过本地环境变量设置，不能写进命令文件、提示词或仓库。
