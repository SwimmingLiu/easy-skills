---
name: llm-wiki-init
description: 将空目录或已有资料目录初始化为可持续回流维护的本地 LLM Wiki，创建 AGENTS.md、raw/wiki/index/outputs/assets 分层、Wiki 索引、概览和维护日志。适用于用户提出“初始化 LLM Wiki”“把这个文件夹变成知识库”“创建 Karpathy 风格知识库”“给资料库加入自动整理/知识回流范式”或要求补齐现有知识库骨架时；默认只新增缺失内容，不覆盖或搬动已有文件。
---

# LLM Wiki 初始化

把目标目录变成“原始资料保留、Wiki 持续编译、成果单独交付”的本地知识库。生成的 `AGENTS.md` 会要求后续 Agent 在实质性任务中主动检索、回流、维护索引和记录日志；同时附带索引重建、质量检查和分享前隐私扫描脚本。

## 初始化流程

1. 确认目标目录。用户说“当前目录”时使用当前工作目录；用户给出路径时使用该路径。不要把 Skill 自身目录误当成目标知识库。
2. 检查目标目录现状，重点查看已有的 `AGENTS.md`、`raw/`、`wiki/`、`index/`、`outputs/` 和用户文件。不要为了套模板而搬动现有资料。
3. 先执行 dry-run：

   ```bash
   python3 <skill-dir>/scripts/init_llm_wiki.py <target-dir> --dry-run
   ```

4. 确认计划只包含补齐操作后正式初始化：

   ```bash
   python3 <skill-dir>/scripts/init_llm_wiki.py <target-dir> --title "知识库名称"
   ```

   `--title` 可省略，默认使用目标目录名。

5. 阅读脚本结果并检查生成的 `wiki/overview.md`。如果目标目录已有明确主题或资料，在不虚构事实的前提下补充概览中的范围、优势、薄弱点和当前优先级。
6. 如果已有同名文件被跳过，保留用户版本并说明冲突。只有用户明确要求合并时，才逐段比较模板与已有文件后做小范围修改。

## 生成结构

脚本创建或补齐以下骨架：

```text
<target>/
├── AGENTS.md
├── README.md
├── SHARE_CHECKLIST.md
├── raw/
│   ├── articles/
│   ├── news/
│   ├── papers/
│   ├── reports/
│   ├── twitter/
│   ├── twitters/
│   ├── wechat/
│   ├── records/
│   ├── youtube-transcript/
│   ├── xiaoyuzhou/
│   └── video/
├── wiki/
│   ├── index.md
│   ├── overview.md
│   ├── log.md
│   ├── sources/
│   ├── topics/
│   ├── entities/
│   ├── analyses/
│   ├── decisions/
│   └── indexes/raw-status.md
├── index/home.md
├── outputs/
├── assets/
└── scripts/
    ├── rebuild_kb_indexes.rb
    ├── kb_lint.rb
    └── privacy_scan.sh
```

空目录中写入 `.gitkeep`，方便版本控制保留目录。模板来自 `assets/templates/`，脚本只替换知识库名称和初始化日期。

## 安全边界

- 默认只创建缺失目录和文件；不提供强制覆盖参数。
- 不重命名、移动、删除已有资料，也不自动初始化 Git。
- 不自动提交、推送、上传、发布或创建后台定时任务。
- 初始化已有资料目录时，只搭骨架；内容迁移要根据实际材料另行、小步执行。
- 自动回流指 Agent 在该目录内完成实质性工作后维护本地 Wiki，不代表后台监听或未经用户授权对外同步。

## 验收

至少检查：

1. `AGENTS.md` 明确要求先读 `wiki/index.md` 和 `wiki/overview.md`。
2. 新资料进入 `raw/` 后，高价值内容会同步到 `wiki/sources/` 和相关主题页，而不只做孤立摘要。
3. 可复用结论、比较和决策分别进入 `wiki/analyses/`、主题页或 `wiki/decisions/`。
4. 导航变化更新 `wiki/index.md`，持久变化追加 `wiki/log.md`。
5. `ruby scripts/rebuild_kb_indexes.rb` 和 `ruby scripts/kb_lint.rb` 可以在空模板上通过。
6. `bash scripts/privacy_scan.sh` 不会发现明显的个人路径、秘密文件或内联凭据。
7. 现有文件内容和未提交改动保持不变。
