<template>
  <!-- 智能问答对话页面 -->
  <div class="chat-container">
    <!-- 左侧知识库选择 -->
    <div class="chat-sidebar">
      <div class="sidebar-title">选择知识库</div>
      <div class="kb-list">
        <div
          v-for="kb in kbList"
          :key="kb.id"
          class="kb-item"
          :class="{ active: selectedKb?.id === kb.id }"
          @click="selectKb(kb)"
        >
          <el-icon><FolderOpened /></el-icon>
          <span class="kb-name">{{ kb.kb_name }}</span>
          <el-tag size="small" type="info">{{ kb.doc_count }}篇</el-tag>
        </div>
      </div>
      <div v-if="kbList.length === 0" class="empty-tip">
        <el-empty description="暂无知识库" :image-size="60" />
      </div>
    </div>

    <!-- 右侧对话区域 -->
    <div class="chat-main">
      <!-- 对话窗口标题 -->
      <div class="chat-header">
        <span v-if="selectedKb">
          <el-icon><ChatDotRound /></el-icon>
          正在查询：{{ selectedKb.kb_name }}
        </span>
        <span v-else class="hint">请先从左侧选择一个知识库</span>
      </div>

      <!-- 消息列表 -->
      <div class="chat-messages" ref="messagesRef">
        <div v-if="messages.length === 0" class="welcome">
          <el-icon :size="64" class="welcome-icon"><ChatDotSquare /></el-icon>
          <h3>欢迎使用企业知识库问答系统</h3>
          <p>请从左侧选择知识库，然后输入您的问题</p>
        </div>
        <ChatMessage v-for="(msg, i) in messages" :key="i" :message="msg" />
      </div>

      <!-- 输入区域 -->
      <div class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="请输入您的问题..."
          :disabled="!selectedKb || asking"
          @keydown.enter.exact.prevent="sendQuestion"
          resize="none"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="asking"
          :disabled="!selectedKb || !question.trim()"
          @click="sendQuestion"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 智能问答对话页面
 * 左侧选择知识库，右侧进行对话
 * 支持多轮对话；正文【n】上标与底部文档来源列表一致
 */
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { getAllKB } from '../api/knowledge'
import { askQuestionStream } from '../api/chat'
import ChatMessage from '../components/ChatMessage.vue'

/** 知识库列表 */
const kbList = ref([])
/** 当前选中的知识库 */
const selectedKb = ref(null)
/** 对话消息列表 */
const messages = ref([])
/** 当前输入的问题 */
const question = ref('')
/** 是否正在请求中 */
const asking = ref(false)
/** 当前会话ID */
const sessionId = ref('')
/** 消息列表DOM引用 */
const messagesRef = ref(null)

/** 加载知识库列表 */
async function loadKBList() {
  try {
    const res = await getAllKB()
    kbList.value = res.data
  } catch (err) {
    // 错误已在拦截器处理
  }
}

/** 选择知识库 */
function selectKb(kb) {
  if (selectedKb.value?.id === kb.id) return
  selectedKb.value = kb
  messages.value = []
  sessionId.value = generateSessionId()
}

/** 生成会话ID */
function generateSessionId() {
  return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

/** 自动滚动到底部 */
async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function updateMessage(index, patch) {
  messages.value[index] = {
    ...messages.value[index],
    ...patch
  }
}

/** 发送问题 */
async function sendQuestion() {
  const q = question.value.trim()
  if (!q || !selectedKb.value || asking.value) return

  messages.value.push({ role: 'user', content: q })
  messages.value.push({ role: 'ai', content: '', sources: [] })
  const aiMessageIndex = messages.value.length - 1
  question.value = ''
  asking.value = true
  scrollToBottom()

  try {
    await askQuestionStream(
      {
        question: q,
        kb_id: selectedKb.value.id,
        session_id: sessionId.value
      },
      {
        onSources: (sources) => {
          updateMessage(aiMessageIndex, { sources })
        },
        onDelta: (delta) => {
          const currentContent = messages.value[aiMessageIndex]?.content || ''
          updateMessage(aiMessageIndex, { content: currentContent + delta })
          scrollToBottom()
        },
        onDone: (data) => {
          updateMessage(aiMessageIndex, {
            content: data.answer || messages.value[aiMessageIndex].content,
            sources: data.source_docs || messages.value[aiMessageIndex].sources
          })
        }
      }
    )
  } catch (err) {
    const errorMessage = err.message || '抱歉，服务出现异常，请稍后重试。'
    updateMessage(aiMessageIndex, { content: errorMessage })
    ElMessage.error(errorMessage)
  } finally {
    asking.value = false
    scrollToBottom()
  }
}

onMounted(() => loadKBList())
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 100px);
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid var(--eq-card-border, rgba(13, 148, 136, 0.12));
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
}

/* 左侧知识库选择栏 */
.chat-sidebar {
  width: 260px;
  border-right: 1px solid rgba(13, 148, 136, 0.12);
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f8fcfb 0%, #f0f7f6 100%);
}

.sidebar-title {
  padding: 16px 20px;
  font-weight: 700;
  font-size: 15px;
  color: #0f172a;
  border-bottom: 1px solid rgba(13, 148, 136, 0.1);
  letter-spacing: -0.02em;
}

.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.kb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}

.kb-item:hover {
  background: rgba(13, 148, 136, 0.1);
}

.kb-item.active {
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
  color: #fff;
  box-shadow: 0 6px 16px rgba(13, 148, 136, 0.35);
}

.kb-item.active .el-tag {
  color: #fff;
  background: rgba(255, 255, 255, 0.2);
  border-color: transparent;
}

.kb-name {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 右侧对话区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 14px 20px;
  border-bottom: 1px solid rgba(13, 148, 136, 0.1);
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #fafdfc 100%);
}

.chat-header .hint {
  color: #64748b;
  font-weight: 500;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-icon {
  color: rgba(13, 148, 136, 0.45);
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
}

.welcome h3 {
  color: #475569;
  font-size: 18px;
  font-weight: 600;
}

.welcome p {
  font-size: 14px;
  color: #94a3b8;
}

/* 输入区域 */
.chat-input {
  padding: 16px 20px;
  border-top: 1px solid rgba(13, 148, 136, 0.1);
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #fafdfc;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 10px;
  border-color: rgba(13, 148, 136, 0.15);
}

.chat-input :deep(.el-textarea__inner:focus) {
  border-color: #0d9488;
  box-shadow: 0 0 0 1px rgba(13, 148, 136, 0.2);
}

.send-btn {
  height: 54px;
  border-radius: 10px;
  font-weight: 600;
}
</style>
