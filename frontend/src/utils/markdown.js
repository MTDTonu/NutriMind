/* markdown 渲染：用于 AI 回答的富文本展示。
 * - html: false  —— 禁用原始 HTML，防止注入与标签被吞导致「乱码」
 * - breaks: true —— 单换行即断行，贴合中文对话习惯
 * - linkify: true —— 自动识别网址
 */
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: false
})

// 外链新窗口打开，避免站内跳转
const defaultLinkOpen =
  md.renderer.rules.link_open ||
  function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options)
  }
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  tokens[idx].attrSet('target', '_blank')
  tokens[idx].attrSet('rel', 'noopener noreferrer')
  return defaultLinkOpen(tokens, idx, options, env, self)
}

/**
 * 清理模型输出：部分模型会把整段回答包进 ```markdown ... ``` 围栏，
 * 直接渲染会变成一整块代码，看起来像「乱码」。这里把这种整体围栏剥掉。
 */
export function stripFence(raw) {
  let s = String(raw || '').trim()
  const m = s.match(/^```[a-zA-Z0-9]*\s*\n([\s\S]*?)\n```\s*$/)
  if (m) return m[1]
  // 流式过程中只有开头围栏（还没输出结尾）：去掉开头那一行
  if (/^```[a-zA-Z0-9]*\s*\n/.test(s)) {
    s = s.replace(/^```[a-zA-Z0-9]*\s*\n/, '')
  }
  return s
}

/** 渲染 markdown 为 HTML 字符串（永不抛错，异常时回退为纯文本转义） */
export function renderMarkdown(text) {
  if (!text) return ''
  try {
    return md.render(stripFence(text))
  } catch (e) {
    return escapeHtml(String(text))
  }
}

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export default md
