<template>
  <!-- 对话历史页面 -->
  <div class="page-container">
    <!-- 筛选栏 -->
    <el-card shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-select
            v-model="queryParams.kb_id"
            placeholder="按知识库筛选"
            clearable
            @change="loadList"
            style="width: 100%"
          >
            <el-option
              v-for="kb in kbOptions"
              :key="kb.id"
              :label="kb.kb_name"
              :value="kb.id"
            />
          </el-select>
        </el-col>
        <el-col :span="16" style="text-align: right">
          <el-button
            type="danger"
            plain
            :disabled="!selectedRows.length"
            @click="handleBatchDelete"
          >
            批量删除{{ selectedRows.length ? `（${selectedRows.length}）` : '' }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史记录表格 -->
    <el-card shadow="never">
      <el-table
        ref="tableRef"
        :data="tableData"
        v-loading="loading"
        stripe
        row-key="id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="48" align="center" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="question" label="问题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="answer" label="回答" min-width="300" show-overflow-tooltip />
        <el-table-column prop="kb_name" label="知识库" width="130" />
        <el-table-column prop="username" label="提问者" width="100" />
        <el-table-column prop="create_time" label="时间" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="showDetail(row)">详情</el-button>
            <el-popconfirm title="确认删除该条对话记录？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadList"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="对话详情" width="650px">
      <div class="detail-content" v-if="currentChat">
        <div class="detail-item">
          <div class="detail-label">提问：</div>
          <div class="detail-value question">{{ currentChat.question }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">回答：</div>
          <div class="detail-value answer">
            <div
              v-for="(block, index) in formattedAnswer"
              :key="index"
              :class="['answer-block', `answer-${block.type}`]"
            >
              {{ block.text }}
            </div>
          </div>
        </div>
        <div class="detail-item" v-if="currentChat.source_docs?.length">
          <div class="detail-label">参考来源：</div>
          <div class="detail-value">
            <el-tag
              v-for="(src, i) in currentChat.source_docs"
              :key="i"
              size="small"
              class="source-tag"
            >
              {{ src.file_name }}
            </el-tag>
          </div>
        </div>
        <div class="detail-item">
          <div class="detail-label">知识库：</div>
          <div class="detail-value">{{ currentChat.kb_name }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">时间：</div>
          <div class="detail-value">{{ currentChat.create_time }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 对话历史页面
 * 展示用户的历史问答记录，支持按知识库筛选、查看详情、单条删除与批量删除
 */
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getChatHistory, deleteChatHistory, batchDeleteChatHistory } from '../api/chat'
import { getAllKB } from '../api/knowledge'

const tableRef = ref(null)
const loading = ref(false)
const detailVisible = ref(false)
const tableData = ref([])
const total = ref(0)
const kbOptions = ref([])
const currentChat = ref(null)
const selectedRows = ref([])

const queryParams = reactive({ page: 1, page_size: 10, kb_id: null })

async function loadKBOptions() {
  const res = await getAllKB()
  kbOptions.value = res.data
}

function clearTableSelection() {
  selectedRows.value = []
  nextTick(() => {
    tableRef.value?.clearSelection()
  })
}

async function loadList() {
  loading.value = true
  try {
    const res = await getChatHistory(queryParams)
    tableData.value = res.data.list
    total.value = res.data.total
    clearTableSelection()
  } finally {
    loading.value = false
  }
}

function onSelectionChange(rows) {
  selectedRows.value = rows
}

function showDetail(row) {
  currentChat.value = row
  detailVisible.value = true
}

async function handleDelete(row) {
  await deleteChatHistory(row.id)
  ElMessage.success('删除成功')
  if (currentChat.value?.id === row.id) {
    detailVisible.value = false
    currentChat.value = null
  }
  await loadList()
}

async function handleBatchDelete() {
  const rows = selectedRows.value
  if (!rows.length) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${rows.length} 条对话记录？`, '批量删除', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  const ids = rows.map((r) => r.id)
  const res = await batchDeleteChatHistory(ids)
  ElMessage.success(res.message || '删除成功')
  const deletedIds = new Set(ids)
  if (currentChat.value && deletedIds.has(currentChat.value.id)) {
    detailVisible.value = false
    currentChat.value = null
  }
  await loadList()
}

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

function formatAnswerContent(content) {
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
}

const formattedAnswer = computed(() => formatAnswerContent(currentChat.value?.answer || ''))

onMounted(() => {
  loadKBOptions()
  loadList()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-item {
  display: flex;
  gap: 8px;
}

.detail-label {
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  min-width: 70px;
}

.detail-value {
  color: #475569;
  line-height: 1.6;
  word-break: break-all;
}

.detail-value.question {
  color: #0d9488;
  font-weight: 600;
}

.detail-value.answer {
  background: #f0fdf9;
  border: 1px solid rgba(13, 148, 136, 0.12);
  padding: 12px;
  border-radius: 10px;
}

.answer-block {
  white-space: pre-wrap;
}

.answer-title {
  margin: 12px 0 6px;
  color: #0f766e;
  font-size: 15px;
  font-weight: 700;
}

.answer-title:first-child {
  margin-top: 0;
}

.answer-list {
  position: relative;
  padding-left: 18px;
  margin: 4px 0;
}

.answer-list::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 0.78em;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #14b8a6;
}

.answer-paragraph {
  margin: 4px 0;
}

.answer-spacer {
  height: 8px;
}

.source-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}
</style>
