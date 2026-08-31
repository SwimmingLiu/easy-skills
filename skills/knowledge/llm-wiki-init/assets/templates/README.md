# {{VAULT_TITLE}}

这是一个本地、可持续维护的 LLM Wiki：

```text
原始资料 raw/  ->  可复用知识 wiki/  ->  任务成果 outputs/
```

## 开始使用

1. 编辑 `wiki/overview.md`，写清范围、目标和主要读者。
2. 用 Obsidian 打开仓库根目录（可选）。
3. 让 Agent 在此目录工作；它会读取根目录的 `AGENTS.md`。
4. 新资料先保留在 `raw/`，再把可复用结论编译到 `wiki/`。

## 维护

```bash
ruby scripts/rebuild_kb_indexes.rb
ruby scripts/kb_lint.rb
bash scripts/privacy_scan.sh
```

本模板不会自动上传、推送或发布任何内容。分享使用后的知识库前，请先阅读 `SHARE_CHECKLIST.md`。

