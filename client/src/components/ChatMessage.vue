<template>
  <!-- 对话消息气泡组件 -->
  <div class="message-wrapper" :class="{ 'is-user': isUser }">
    <div class="avatar">
      <el-avatar :size="36" :icon="isUser ? UserFilled : Monitor" :style="avatarStyle" />
    </div>
    <div class="bubble" :class="{ 'user-bubble': isUser, 'ai-bubble': !isUser }">
      <div class="message-text">
        <template v-if="isUser">
          <div class="content-plain">{{ message.content }}</div>
        </template>
        <template v-else>
          <div v-if="aiRenderedHtml" class="message-markdown-wrap">
            <div class="message-markdown" v-html="aiRenderedHtml"></div>
          </div>
          <span v-else class="streaming-placeholder">思考中...</span>
        </template>
      </div>
      <div v-if="!isUser && displaySources.length" class="sources">
        <div class="sources-title">文档来源:</div>
        <div class="source-rows">
          <div
            v-for="(src, i) in displaySources"
            :key="sourceRowKey(src, i)"
            class="source-row"
          >
            <span v-if="src.citeNote" class="source-cite-note">（引用 {{ src.citeNote }}）</span>
            <span v-else-if="typeof src.ref_index === 'number'" class="source-ref">【{{ src.ref_index }}】</span>
            <span class="source-meta">{{ src.file_name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 对话消息气泡组件
 * 区分用户消息和 AI 回答；AI 内容按 Markdown 渲染；正文【n】上标 + 底部文档来源列表
 */
import { computed } from 'vue'
import { UserFilled, Monitor } from '@element-plus/icons-vue'
import { renderSafeMarkdown } from '../utils/renderMarkdown.js'
import { normalizeSourceDocsForDisplay } from '../utils/sourceDocsDisplay.js'

const props = defineProps({
  /** 消息对象 { role: 'user'|'ai', content: string, sources?: array } */
  message: { type: Object, required: true }
})

const aiRenderedHtml = computed(() => renderSafeMarkdown(props.message.content || ''))

const displaySources = computed(() => normalizeSourceDocsForDisplay(props.message.sources || []))

/** 是否为用户消息 */
const isUser = computed(() => props.message.role === 'user')

/** 头像样式 */
const avatarStyle = computed(() => ({
  backgroundColor: isUser.value ? '#0d9488' : '#14b8a6'
}))

function sourceRowKey(src, i) {
  if (src?.citeNote) return `cite-${src.file_name || ''}-${src.citeNote}`
  const d = src?.doc_id
  if (d) return `d-${d}`
  return `f-${src?.file_name || ''}-${src?.ref_index ?? i}`
}
</script>

<style scoped>
.message-wrapper {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message-wrapper.is-user {
  flex-direction: row-reverse;
}

.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.user-bubble {
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
  color: #fff;
  border-top-right-radius: 4px;
  box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
}

.ai-bubble {
  background: #f0fdf9;
  border: 1px solid rgba(13, 148, 136, 0.12);
  color: #1e293b;
  border-top-left-radius: 4px;
}

.message-text {
  font-size: 14px;
}

.content-plain {
  white-space: pre-wrap;
  word-break: break-word;
}

.message-markdown-wrap {
  overflow-x: auto;
  max-width: 100%;
}

.message-markdown {
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b;
}

.message-markdown :deep(h1),
.message-markdown :deep(h2),
.message-markdown :deep(h3),
.message-markdown :deep(h4),
.message-markdown :deep(h5),
.message-markdown :deep(h6) {
  margin: 12px 0 6px;
  color: #0f766e;
  font-weight: 700;
}

.message-markdown :deep(h1:first-child),
.message-markdown :deep(h2:first-child),
.message-markdown :deep(h3:first-child),
.message-markdown :deep(h4:first-child),
.message-markdown :deep(h5:first-child),
.message-markdown :deep(h6:first-child) {
  margin-top: 0;
}

.message-markdown :deep(p) {
  margin: 4px 0;
}

.message-markdown :deep(ul),
.message-markdown :deep(ol) {
  margin: 4px 0;
  padding-left: 1.4em;
}

.message-markdown :deep(li) {
  margin: 2px 0;
}

.message-markdown :deep(table) {
  width: max-content;
  max-width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
  font-size: 13px;
}

.message-markdown :deep(th),
.message-markdown :deep(td) {
  border: 1px solid rgba(13, 148, 136, 0.35);
  padding: 6px 10px;
  text-align: left;
  vertical-align: top;
}

.message-markdown :deep(th) {
  background: rgba(20, 184, 166, 0.12);
  font-weight: 600;
  color: #0f766e;
}

.message-markdown :deep(pre) {
  margin: 8px 0;
  padding: 10px 12px;
  overflow-x: auto;
  background: rgba(15, 118, 110, 0.08);
  border-radius: 8px;
  font-size: 13px;
}

.message-markdown :deep(code) {
  padding: 0.15em 0.4em;
  background: rgba(15, 118, 110, 0.1);
  border-radius: 4px;
  font-size: 0.92em;
}

.message-markdown :deep(pre code) {
  padding: 0;
  background: none;
  font-size: inherit;
}

.message-markdown :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 0 4px 12px;
  border-left: 3px solid rgba(20, 184, 166, 0.45);
  color: #475569;
}

.message-markdown :deep(a) {
  color: #0d9488;
  word-break: break-all;
}

.message-markdown :deep(sup.eq-cite) {
  display: inline-block;
  vertical-align: super;
  font-size: 0.68em;
  line-height: 0;
  font-weight: 700;
  color: #0d9488;
  margin-left: 0.08em;
  position: relative;
  top: -0.02em;
  text-decoration: none;
  border: none;
  background: none;
  padding: 0;
}

.message-markdown :deep(hr) {
  margin: 12px 0;
  border: none;
  border-top: 1px solid rgba(13, 148, 136, 0.2);
}

.streaming-placeholder {
  color: #64748b;
}

.sources {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(13, 148, 136, 0.15);
}

.sources-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.source-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
  font-size: 13px;
  color: #ed0909;
}

.source-ref {
  font-weight: 700;
  color: #f40404;
  flex-shrink: 0;
}

.source-cite-note {
  font-size: 12px;
  color: #e4091b;
  flex-shrink: 0;
}

.source-meta {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}
</style>
