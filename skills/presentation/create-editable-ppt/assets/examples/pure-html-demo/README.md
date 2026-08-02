# Pure HTML PPT 示例

主题：`editorial`

这个示例使用 `pure-html` 模式：文字来自 `deck_spec.json`，版式和抽象装饰由 HTML/CSS 渲染，不调用 imagegen，也不包含 `assets/` 图片目录。修改 `deck_spec.json` 中的 `exact_text` 后重新执行 `render` 即可查看文字变化。

入口：

- `index.html`：本地翻页版本
- `dist/presentation.pure-html.html`：无外部资源的单文件 Bundle
- `qa/desktop.png`、`qa/mobile.png`：桌面与窄屏检查截图
