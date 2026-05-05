<template>
  <!-- 对话消息气泡组件 -->
  <div class="message-wrapper" :class="{ 'is-user': isUser }">
    <div class="avatar">
      <el-avatar :size="36" :icon="isUser ? UserFilled : Monitor" :style="avatarStyle" />
    </div>
    <div class="bubble" :class="{ 'user-bubble': isUser, 'ai-bubble': !isUser }">
      <div class="message-text">
        <template v-if="formattedContent.length">
          <div
            v-for="(block, index) in formattedContent"
            :key="index"
            :class="['content-block', `content-${block.type}`]"
          >
            {{ block.text }}
          </div>
        </template>
        <span v-else class="streaming-placeholder">思考中...</span>
      </div>
      <!-- AI回答时显示参考来源 -->
      <div v-if="!isUser && message.sources?.length" class="sources">
        <div class="sources-title">参考来源：</div>
        <el-tag
          v-for="(src, i) in message.sources"
          :key="i"
          size="small"
          type="info"
          class="source-tag"
        >
          {{ src.file_name }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 对话消息气泡组件
 * 区分用户消息和AI回答，AI回答可展示参考来源
 */
import { computed } from 'vue'
import { UserFilled, Monitor } from '@element-plus/icons-vue'

const props = defineProps({
  /** 消息对象 { role: 'user'|'ai', content: string, sources?: array } */
  message: { type: Object, required: true }
})

function cleanTitle(text) {
  return text
    .replace(/^\s{0,3}#{1,6}\s*/, '')
    .replace(/^\s*[-*+]\s+/, '')
    .replace(/\*+/g, '')
    .replace(/：\s*$/, '')
    .trim()
}

function isContentTitle(line) {
  const trimmed = line.trim()
  if (!trimmed) return false
  if (/^#{1,6}\s+/.test(trimmed)) return true
  if (/^\*{1,3}[^*]+\*{1,3}\s*[:：]?$/.test(trimmed)) return true
  if (/^#{1,6}\s*\*+/.test(trimmed)) return true
  return false
}

function stripInlineMarkdown(text) {
  return text.replace(/\*{1,3}([^*]+?)\*{1,3}/g, '$1').trim()
}

const formattedContent = computed(() => {
  const content = props.message.content || ''
  if (!content) return []

  return content
    .split(/\r?\n/)
    .map((line) => {
      if (isContentTitle(line)) {
        return { type: 'title', text: cleanTitle(line) }
      }

      const trimmed = line.trim()
      if (/^([-*+]\s+|\d+[.)、]\s*)/.test(trimmed)) {
        return { type: 'list', text: stripInlineMarkdown(trimmed) }
      }

      return { type: trimmed ? 'paragraph' : 'spacer', text: stripInlineMarkdown(line) }
    })
})

/** 是否为用户消息 */
const isUser = computed(() => props.message.role === 'user')

/** 头像样式 */
const avatarStyle = computed(() => ({
  backgroundColor: isUser.value ? '#0d9488' : '#14b8a6'
}))
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

.content-block {
  white-space: pre-wrap;
}

.content-title {
  margin: 12px 0 6px;
  color: #0f766e;
  font-size: 15px;
  font-weight: 700;
}

.content-title:first-child {
  margin-top: 0;
}

.content-list {
  position: relative;
  padding-left: 18px;
  margin: 4px 0;
}

.content-list::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 0.78em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #14b8a6;
}

.content-paragraph {
  margin: 4px 0;
}

.content-spacer {
  height: 8px;
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
  margin-bottom: 4px;
}

.source-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}
</style>
