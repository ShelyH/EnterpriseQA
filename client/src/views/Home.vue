<template>
  <!-- 管理员首页 - 数据统计概览 -->
  <div class="home-container">
    <!-- 统计卡片区域 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">用户总数</span>
              <span class="stat-value">{{ stats.user_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#0d9488"><User /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">知识库数量</span>
              <span class="stat-value">{{ stats.kb_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#14b8a6"><FolderOpened /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">文档总数</span>
              <span class="stat-value">{{ stats.doc_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#0ea5e9"><Document /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">今日提问</span>
              <span class="stat-value">{{ stats.today_chat_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#f97316"><ChatDotRound /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">近7天提问趋势</span>
          </template>
          <div ref="trendChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">知识库文档占比</span>
          </template>
          <div ref="pieChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
/**
 * 管理员首页
 * 展示统计卡片和ECharts图表（提问趋势折线图 + 知识库文档占比饼图）
 */
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { getOverview } from '../api/stats'

/** 统计数据 */
const stats = reactive({
  user_count: 0,
  kb_count: 0,
  doc_count: 0,
  today_chat_count: 0,
  trend_data: [],
  kb_doc_data: []
})

/** 图表DOM引用 */
const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart = null
let pieChart = null

/** 加载统计数据 */
async function loadStats() {
  try {
    const res = await getOverview()
    Object.assign(stats, res.data)
    renderTrendChart()
    renderPieChart()
  } catch (err) {
    // 错误已在拦截器中处理
  }
}

/** 渲染近7天提问趋势折线图 */
function renderTrendChart() {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value)

  const dates = stats.trend_data.map(item => item.date)
  const counts = stats.trend_data.map(item => item.count)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [{
      name: '提问次数',
      type: 'line',
      smooth: true,
      data: counts,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(13, 148, 136, 0.35)' },
          { offset: 1, color: 'rgba(13, 148, 136, 0.04)' }
        ])
      },
      lineStyle: { color: '#0d9488', width: 2 },
      itemStyle: { color: '#14b8a6' }
    }]
  })
}

/** 渲染知识库文档占比饼图 */
function renderPieChart() {
  if (!pieChartRef.value) return
  pieChart = echarts.init(pieChartRef.value)

  const data = stats.kb_doc_data.length > 0
    ? stats.kb_doc_data
    : [{ name: '暂无数据', value: 1 }]

  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center'
    },
    color: ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#0ea5e9', '#64748b', '#f97316'],
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' }
      },
      data: data
    }]
  })
}

/** 窗口大小变化时重绘图表 */
function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(() => {
  loadStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stat-card {
  border-radius: 12px;
  border: 1px solid var(--eq-card-border, rgba(13, 148, 136, 0.12));
  overflow: hidden;
}

.stat-card :deep(.el-card__body) {
  padding: 20px 22px;
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 14px;
  color: #64748b;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.03em;
}

.stat-icon {
  opacity: 0.8;
}

.home-container :deep(.el-card) {
  border: 1px solid var(--eq-card-border, rgba(13, 148, 136, 0.12));
}

.card-title {
  font-weight: 600;
  font-size: 15px;
  color: #0f172a;
}

.chart-box {
  width: 100%;
  height: 320px;
}
</style>
