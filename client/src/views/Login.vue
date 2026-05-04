<template>
  <!-- 登录页面 -->
  <div class="login-page">
    <div class="login-bg" aria-hidden="true" />
    <div class="login-card">
      <div class="login-header">
        <div class="logo-ring">
          <el-icon :size="28" class="logo-icon"><ChatDotSquare /></el-icon>
        </div>
        <h2>企业知识库问答系统</h2>
        <p class="subtitle">基于 RAG 的智能知识检索与问答</p>
      </div>
      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            size="large"
            class="login-btn"
            native-type="button"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <p class="login-hint">请使用企业分配的账号登录</p>
    </div>
  </div>
</template>

<script setup>
/**
 * 登录页面
 * 支持用户名密码登录，登录成功后跳转至对应首页
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

/** 登录表单 */
const loginForm = reactive({
  username: '',
  password: ''
})

/** 表单校验规则 */
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

/** 处理登录 */
async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(loginForm)
    userStore.setLoginInfo(res.data)
    ElMessage.success('登录成功')
    // 管理员跳转数据概览，普通用户跳转智能问答
    if (res.data.user.role === 'admin') {
      router.push('/home')
    } else {
      router.push('/chat')
    }
  } catch (err) {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 90% 55% at 50% -15%, rgba(45, 212, 191, 0.22), transparent 55%),
    radial-gradient(ellipse 50% 45% at 100% 80%, rgba(56, 189, 248, 0.12), transparent),
    linear-gradient(168deg, #0f172a 0%, #134e4a 42%, #0f766e 100%);
  pointer-events: none;
}

.login-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black 20%, transparent 70%);
}

.login-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 44px 40px 36px;
  background: linear-gradient(180deg, #fafbfc 0%, #f4f6f8 100%);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 32px 64px -16px rgba(15, 23, 42, 0.55),
    0 0 0 1px rgba(15, 118, 110, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-ring {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 4px;
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(13, 148, 136, 0.15), rgba(45, 212, 191, 0.08));
  border: 1px solid rgba(13, 148, 136, 0.25);
}

.logo-icon {
  color: #0d9488;
}

.login-header h2 {
  margin: 14px 0 8px;
  color: #0f172a;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}

.login-form {
  margin-top: 8px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding-left: 14px;
  padding-right: 14px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  background: #fff;
  transition: box-shadow 0.2s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #cbd5e1 inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px #0d9488 inset,
    0 0 0 4px rgba(13, 148, 136, 0.12);
}

.login-form :deep(.login-btn) {
  width: 100%;
  height: 46px;
  margin-top: 4px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.08em;
  color: #fff;
  border: none;
  background: linear-gradient(135deg, #14b8a6 0%, #0d9488 55%, #0f766e 100%);
  box-shadow: 0 10px 24px -8px rgba(13, 148, 136, 0.65);
}

.login-form :deep(.login-btn:hover),
.login-form :deep(.login-btn:focus) {
  color: #fff;
  background: linear-gradient(135deg, #2dd4bf 0%, #14b8a6 50%, #0d9488 100%);
  box-shadow: 0 14px 28px -6px rgba(13, 148, 136, 0.55);
}

.login-form :deep(.login-btn:active) {
  color: #fff;
  background: linear-gradient(135deg, #0d9488 0%, #115e59 100%);
}

.login-hint {
  margin: 20px 0 0;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}
</style>
