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
            <div v-if="answerHtml" class="message-markdown-wrap">
              <div class="message-markdown" v-html="answerHtml"></div>
            </div>
          </div>
        </div>
        <div class="detail-item" v-if="displaySourceDocs.length">
          <div class="detail-label">文档来源：</div>
          <div class="detail-value source-detail">
            <div
              v-for="(src, i) in displaySourceDocs"
              :key="sourceRowKey(src, i)"
              class="source-row"
            >
              <span v-if="src.citeNote" class="source-cite-note">（引用 {{ src.citeNote }}）</span>
              <span v-else-if="typeof src.ref_index === 'number'" class="source-ref">【{{ src.ref_index }}】</span>
              <span class="source-meta">{{ src.file_name }}</span>
            </div>
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
import { renderSafeMarkdown } from '../utils/renderMarkdown.js'
import { normalizeSourceDocsForDisplay } from '../utils/sourceDocsDisplay.js'

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

const answerHtml = computed(() => renderSafeMarkdown(currentChat.value?.answer || ''))

const displaySourceDocs = computed(() =>
  normalizeSourceDocsForDisplay(currentChat.value?.source_docs || [])
)

function sourceRowKey(src, i) {
  if (src?.citeNote) return `cite-${src.file_name || ''}-${src.citeNote}`
  const d = src?.doc_id
  if (d) return `d-${d}`
  return `f-${src?.file_name || ''}-${src?.ref_index ?? i}`
}

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
  min-height: 0;
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

.message-markdown :deep(code.eq-cite) {
  color: #dc2626;
  font-weight: 700;
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.22);
  padding: 0.12em 0.38em;
  border-radius: 4px;
  font-size: 0.88em;
  vertical-align: baseline;
  line-height: 1.35;
}

.message-markdown :deep(pre code.eq-cite) {
  padding: inherit;
  border: none;
  background: inherit;
  color: inherit;
  font-weight: inherit;
  font-size: inherit;
}

.message-markdown :deep(hr) {
  margin: 12px 0;
  border: none;
  border-top: 1px solid rgba(13, 148, 136, 0.2);
}

.source-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 10px;
  font-size: 13px;
  color: #334155;
}

.source-ref {
  font-weight: 700;
  color: #0f766e;
  flex-shrink: 0;
}

.source-cite-note {
  font-size: 12px;
  color: #64748b;
  flex-shrink: 0;
}

.source-meta {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}
</style>
