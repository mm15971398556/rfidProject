// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import IssueReasons from '../views/IssueReasons.vue'
import MaintainerConfig from '../views/MaintainerConfig.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: '条码统计仪表板'
    }
  },
  {
    path: '/issue-reasons',
    name: 'IssueReasons',
    component: IssueReasons,
    meta: {
      title: '问题原因管理'
    }
  },
  {
    path: '/maintainer-config',
    name: 'MaintainerConfig',
    component: MaintainerConfig,
    meta: {
      title: '条码维护人配置'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 设置页面标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 条码扫描统计系统`
  }
  next()
})

export default router