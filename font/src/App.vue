<!-- src/App.vue -->
<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-content">
        <div class="logo">
          <h1>
            <el-icon><DataLine /></el-icon>
            条码扫描统计系统
          </h1>
        </div>
        
        <!-- 导航菜单 -->
        <nav class="nav-menu">
          <el-menu
            :default-active="currentRoute"
            mode="horizontal"
            router
            class="nav-menu-items"
          >
            <el-menu-item index="/">
              <el-icon><DataBoard /></el-icon>
              <span>数据统计</span>
            </el-menu-item>
            <el-menu-item index="/issue-reasons">
              <el-icon><Setting /></el-icon>
              <span>问题原因管理</span>
            </el-menu-item>
            <el-menu-item index="/maintainer-config">
              <el-icon><User /></el-icon>
              <span>维护人配置</span>
            </el-menu-item>
          </el-menu>
        </nav>
      </div>
    </header>
    
    <!-- 主内容区域 -->
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataLine, DataBoard, Setting, User } from '@element-plus/icons-vue'

const route = useRoute()

// 计算当前路由
const currentRoute = computed(() => route.path)
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
}

.logo h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-menu {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu-items {
  background: transparent;
  border: none;
  display: flex;
  gap: 0;
}

.nav-menu-items :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.8) !important;
  border: none !important;
  font-size: 14px;
  font-weight: 500;
  min-width: 120px;
  justify-content: center;
  margin: 0 4px;
  transition: all 0.3s ease;
}

.nav-menu-items :deep(.el-menu-item:hover) {
  color: white !important;
  background: rgba(255, 255, 255, 0.1) !important;
}

.nav-menu-items :deep(.el-menu-item.is-active) {
  color: white !important;
  background: rgba(255, 255, 255, 0.2) !important;
  border-bottom: 2px solid white !important;
}

.app-main {
  flex: 1;
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    height: auto;
    padding: 10px 20px;
  }
  
  .logo {
    margin-bottom: 10px;
  }
  
  .nav-menu {
    width: 100%;
  }
  
  .app-main {
    padding: 10px;
  }
}
</style>