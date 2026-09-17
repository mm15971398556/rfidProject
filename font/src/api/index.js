// src/api/index.js
import axios from 'axios'

// 获取API基础URL
const getBaseURL = () => {
  if (import.meta.env.PROD) {
    return import.meta.env.VITE_API_URL || '/api'
  }
  return '/api'
}

// 创建axios实例
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 统计相关API
export const statsApi = {
  // 按条码统计（支持分页）
  getBarcodeStats(params) {
    return api.get('/stats/by-barcode', { params })
  },
  
  // 按日期统计
  getDateStats(params) {
    return api.get('/stats/by-date', { params })
  },
  
  // 获取热门条码
  getTopBarcodes(limit = 20) {
    return api.get('/stats/top-barcodes', { params: { limit } })
  },
  
  // 获取可用日期
  getAvailableDates() {
    return api.get('/stats/available-dates')
  },
  
  // 搜索条码
  searchBarcode(q) {
    return api.get('/stats/search-barcode', { params: { q } })
  },
  
  // 获取系统状态
  getSystemStatus() {
    return api.get('/system/status')
  },
  
  // 获取活跃客户端
  getActiveClients() {
    return api.get('/system/clients')
  }
}

// 问题原因相关API
export const issueApi = {
  // 更新条码问题原因
  updateBarcodeIssueReason(data) {
    return api.post('/issue/update', data)
  },
  
  // 获取条码问题信息
  getIssueInfo(barcode) {
    return api.get('/issue/info', { params: { barcode } })
  },
  
  // 获取问题原因列表
  getIssueReasons(params) {
    return api.get('/issue-reasons', { params })
  },
  
  // 创建问题原因
  createIssueReason(data) {
    return api.post('/issue-reasons', data)
  },
  
  // 更新问题原因分类
  updateIssueReason(id, data) {
    return api.put(`/issue-reasons/${id}`, data)
  },
  
  // 删除问题原因
  deleteIssueReason(id) {
    return api.delete(`/issue-reasons/${id}`)
  }
}

// 条码维护人配置相关API
export const maintainerApi = {
  // 分页查询
  getList(params) {
    return api.get('/maintainers', { params })
  },
  // 全量字典 {barcode: maintainer_name}
  getAll() {
    return api.get('/maintainers/all')
  },
  create(data) {
    return api.post('/maintainers', data)
  },
  update(id, data) {
    return api.put(`/maintainers/${id}`, data)
  },
  delete(id) {
    return api.delete(`/maintainers/${id}`)
  }
}

// 默认导出所有API方法
const apiMethods = {
  ...statsApi,
  ...issueApi,
  maintainerApi
}

export default apiMethods