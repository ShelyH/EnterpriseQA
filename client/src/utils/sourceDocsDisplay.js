/**
 * 规范文档引用列表用于展示（兼容仅 ref_index 的新数据与含 ref_indexes 的旧数据）。
 * @param {unknown[]} sources
 * @returns {Array<{ ref_index?: number, citeNote?: string, file_name: string, doc_id: string }>}
 */
export function normalizeSourceDocsForDisplay(sources) {
  if (!Array.isArray(sources) || !sources.length) return []

  const hasRefIndexes = sources.some((s) => Array.isArray(s?.ref_indexes) && s.ref_indexes.length > 0)
  if (hasRefIndexes) {
    return sources.map((s) => {
      const refs = [...(s.ref_indexes || [])]
        .filter((x) => typeof x === 'number')
        .sort((a, b) => a - b)
      if (refs.length > 1) {
        return {
          file_name: s.file_name || '未知来源',
          doc_id: s.doc_id || '',
          citeNote: refs.join('、')
        }
      }
      const n =
        refs.length === 1 ? refs[0] : typeof s.ref_index === 'number' ? s.ref_index : undefined
      return {
        ref_index: n,
        file_name: s.file_name || '未知来源',
        doc_id: s.doc_id || ''
      }
    })
  }

  return [...sources]
    .map((s) => ({
      ref_index: typeof s.ref_index === 'number' ? s.ref_index : undefined,
      file_name: s.file_name || '未知来源',
      doc_id: s.doc_id || ''
    }))
    .sort((a, b) => (a.ref_index ?? 0) - (b.ref_index ?? 0))
}
