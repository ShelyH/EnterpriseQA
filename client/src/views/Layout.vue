<template>
  <!-- 后台主布局：左侧菜单 + 顶栏 + 内容区 -->
  <el-container class="layout-container">
    <!-- 左侧菜单栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="24"><ChatDotSquare /></el-icon>
        <span v-show="!isCollapse" class="logo-text">企业知识库问答系统</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        :router="true"
        class="aside-menu"
      >
        <el-menu-item v-if="userStore.isAdmin" index="/home">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>数据概览</template>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能问答</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/knowledge-base">
          <el-icon><FolderOpened /></el-icon>
          <template #title>知识库管理</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/document">
          <el-icon><Document /></el-icon>
          <template #title>文档管理</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/user-manage">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item index="/chat-history">
          <el-icon><Clock /></el-icon>
          <template #title>对话历史</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <span class="page-title">{{ $route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.userInfo?.nickname }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
/**
 * 后台布局组件
 * 包含侧边栏（根据角色动态显示菜单）、顶部栏和内容区
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { UserFilled } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

/** 控制侧边栏折叠 */
const isCollapse = ref(false)

/** 处理下拉菜单命令 */
function handleCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background: linear-gradient(180deg, #0f172a 0%, #134e4a 55%, #115e59 100%);
  transition: width 0.3s;
  overflow: hidden;
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.18);
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ecfdf5;
  gap: 8px;
  border-bottom: 1px solid rgba(94, 234, 212, 0.15);
  background: rgba(15, 23, 42, 0.35);
}

.logo .el-icon {
  color: #5eead4;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.aside-menu {
  border-right: none;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(226, 232, 240, 0.88);
  --el-menu-hover-text-color: #ecfdf5;
  --el-menu-hover-bg-color: rgba(45, 212, 191, 0.12);
  --el-menu-active-color: #5eead4;
  background: transparent !important;
}

.aside-menu :deep(.el-menu-item) {
  border-radius: 10px;
  margin: 4px 8px;
  width: calc(100% - 16px);
}

.aside-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(
    90deg,
    rgba(13, 148, 136, 0.45) 0%,
    rgba(13, 148, 136, 0.12) 100%
  ) !important;
  border-right: none;
  box-shadow: inset 3px 0 0 #5eead4;
}

.aside-menu.el-menu--collapse :deep(.el-menu-item.is-active) {
  box-shadow: none;
  border-left: 3px solid #5eead4;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--eq-card-border);
  background: linear-gradient(180deg, #ffffff 0%, #f8fcfb 100%);
  padding: 0 22px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #475569;
  padding: 6px;
  border-radius: 8px;
  transition: background 0.2s, color 0.2s;
}

.collapse-btn:hover {
  color: #0d9488;
  background: rgba(13, 148, 136, 0.08);
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.header-right .user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 10px;
  transition: background 0.2s;
}

.header-right .user-info:hover {
  background: rgba(13, 148, 136, 0.08);
}

.username {
  font-size: 14px;
  color: #475569;
  font-weight: 500;
}

.main {
  background: var(--eq-surface);
  padding: 20px;
  overflow-y: auto;
}
</style>
