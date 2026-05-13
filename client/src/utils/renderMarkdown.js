import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.use({
  gfm: true,
  breaks: true
})

const ALLOWED_TAGS = [
  'a',
  'blockquote',
  'br',
  'code',
  'del',
  'div',
  'em',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'hr',
  'i',
  'img',
  'input',
  'li',
  'ol',
  'p',
  'pre',
  's',
  'strong',
  'sub',
  'sup',
  'table',
  'tbody',
  'td',
  'tfoot',
  'th',
  'thead',
  'tr',
  'ul'
]

const ALLOWED_ATTR = [
  'href',
  'title',
  'alt',
  'src',
  'align',
  'colspan',
  'rowspan',
  'type',
  'checked',
  'disabled'
]

const PURIFY = {
  ALLOWED_TAGS,
  ALLOWED_ATTR,
  ALLOW_DATA_ATTR: false
}

/**
 * 将 Markdown 转为可安全用于 v-html 的 HTML（含 GFM 表格等）。
 * @param {string} markdown
 * @returns {string}
 */
export function renderSafeMarkdown(markdown) {
  const src = typeof markdown === 'string' ? markdown : ''
  if (!src.trim()) return ''
  const dirty = marked.parse(src, { async: false })
  return DOMPurify.sanitize(dirty, PURIFY)
}
