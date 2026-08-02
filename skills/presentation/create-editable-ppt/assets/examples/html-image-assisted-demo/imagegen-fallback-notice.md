# 样例素材说明

当前环境的 imagegen CLI 请求因外部账户没有 active plan 未执行。为了让双模式样例仍然可打开，本目录的三个 PNG 由仓库内已有演示照片转换而来，并保留在 manifest 的同一输出路径中。它们只用于演示 HTML 版式、素材槽位和离线 bundle，不代表新生成的 AI 图片。

真实生成时，运行 `node scripts/ppt.mjs doctor --json` 检查本机配置，并把本机的 imagegen 结果替换到 `assets/`。不要在聊天、提示词、日志或项目文件中粘贴密钥。
