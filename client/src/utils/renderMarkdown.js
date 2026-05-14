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
  'disabled',
  'class'
]

const PURIFY = {
  ALLOWED_TAGS,
  ALLOWED_ATTR,
  ALLOW_DATA_ATTR: false
}

const FENCED_CODE_SPLIT = /(```[\s\S]*?```)/g
const INLINE_CODE_SPLIT = /(`[^`]*`)/g

/**
 * 在「非代码」片段中把【n】包成带 class 的 inline code HTML，便于与 Markdown 行内代码样式一致；
 * fenced 代码块与行内 `...` 内不处理，避免破坏代码内容。
 */
function injectCitationAsInlineCode(text) {
  return text.split(FENCED_CODE_SPLIT).map((fenceOrBody) => {
    if (fenceOrBody.startsWith('```')) return fenceOrBody
    return fenceOrBody.split(INLINE_CODE_SPLIT).map((chunk) => {
      if (chunk.startsWith('`') && chunk.endsWith('`') && chunk.length >= 2) return chunk
      return chunk.replace(/【(\d+)】/g, '<code class="eq-cite" title="引用 $1">【$1】</code>')
    }).join('')
  }).join('')
}

/**
 * 将 Markdown 转为可安全用于 v-html 的 HTML（含 GFM 表格等）。
 * @param {string} markdown
 * @returns {string}
 */
export function renderSafeMarkdown(markdown) {
  const src = typeof markdown === 'string' ? markdown : ''
  if (!src.trim()) return ''
  const dirty = marked.parse(injectCitationAsInlineCode(src), { async: false })
  return DOMPurify.sanitize(dirty, PURIFY)
}
