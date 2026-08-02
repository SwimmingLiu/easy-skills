# HTML + AI 图片模式样例

这个样例复用“AI 原生知识工作流”的三页内容，主题为 `editorial`。标题、支持句和流程步骤由 HTML 渲染；右侧或全幅的视觉素材属于 imagegen 槽位，提示词要求不出现任何文字。

打开 `index.html` 查看可翻页版本，打开 `dist/presentation.html-image-assisted.html` 查看可离线分发的单文件包。修改 `deck_spec.json` 中的 `exact_text` 后重新执行 `render` 即可验证文字变化，不需要把文字重新画进图片。
