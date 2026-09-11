<!-- src/components/BarcodeTable.vue -->
<template>
  <el-card class="table-card">
    <template #header>
      <div class="table-header">
        <span>📋 条码扫描明细</span>
        <el-button 
          type="success" 
          size="small" 
          @click="handleExport"
          :disabled="!data.length"
        >
          <el-icon><Download /></el-icon> 导出CSV
        </el-button>
      </div>
    </template>
    
    <el-table 
      :data="data" 
      v-loading="loading"
      style="width: 100%"
      border
      stripe
    >
      <el-table-column prop="barcode" label="条码" min-width="200">
        <template #default="{ row }">
          <el-tooltip
            :content="row.barcode"
            placement="top"
            :disabled="row.barcode.length <= 30"
          >
            <span>{{ formatBarcode(row.barcode) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      
      <el-table-column prop="scan_count" label="扫描次数" width="120" sortable>
        <template #default="{ row }">
          <el-tag :type="getCountType(row.scan_count)">
            {{ row.scan_count }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="device_count" label="设备数" width="100" sortable />
      
      <el-table-column prop="scan_time" label="扫描时间" width="180" sortable>
        <template #default="{ row }">
          {{ formatDateTime(row.scan_time) }}
        </template>
      </el-table-column>
      
      <el-table-column label="设备IP" min-width="150">
        <template #default="{ row }">
          <el-tag size="small" type="info">
            {{ row.devices || '未知' }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="维护人" width="120" sortable>
        <template #default="{ row }">
          <el-tag size="small" type="primary">
            {{ getMaintainer(row.barcode) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="问题原因" width="200" fixed="right">
        <template #default="{ row }">
          <div class="issue-reason-selector">
            <el-select
              v-model="row.issue_reason_id"
              placeholder="搜索或选择问题原因"
              clearable
              filterable
              remote
              :remote-method="searchIssueReasons"
              :filter-method="filterIssueReasons"
              @change="(val) => handleIssueReasonChange(row, val)"
              style="width: 180px;"
            >
              <el-option label="无问题" :value="null" />
              <el-option
                v-for="reason in filteredIssueReasons"
                :key="reason.id"
                :label="reason.reason_name"
                :value="reason.id"
              />
            </el-select>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column label="问题状态" width="100" fixed="right">
        <template #default="{ row }">
          <el-select
            v-model="row.issue_status"
            placeholder="状态"
            @change="(val) => handleIssueStatusChange(row, val)"
            style="width: 80px;"
          >
            <el-option label="正常" value="normal" />
            <el-option label="待处理" value="pending" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </el-card>
</template>

<script setup>
import { computed, ref, reactive, onMounted, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import api from '../api'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  pagination: {
    type: Object,
    default: () => ({
      currentPage: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0
    })
  }
})

const emit = defineEmits(['page-change', 'size-change', 'view-detail', 'issue-updated'])

// 问题原因相关状态
const issueReasons = ref([])
const filteredIssueReasons = ref([])
const searchQuery = ref('')

// 获取问题原因列表（获取所有已启用的）
const loadIssueReasons = async () => {
  try {
    // 获取所有已启用的问题原因，不分页
    const response = await api.getIssueReasons({ 
      is_active: true,
      page: 1,
      pageSize: 1000  // 获取所有记录
    })
    if (response.success) {
      issueReasons.value = response.data || []
      filteredIssueReasons.value = issueReasons.value
      console.log('加载问题原因成功:', issueReasons.value.length, '条')
    }
  } catch (error) {
    console.error('加载问题原因失败:', error)
  }
}

// 远程搜索方法
const searchIssueReasons = (query) => {
  searchQuery.value = query
  if (query) {
    filteredIssueReasons.value = issueReasons.value.filter(reason => {
      return reason.reason_name.toLowerCase().includes(query.toLowerCase())
    })
  } else {
    filteredIssueReasons.value = issueReasons.value
  }
}

// 本地过滤方法
const filterIssueReasons = (query) => {
  searchIssueReasons(query)
}

// 根据问题原因文本查找对应的 ID
const findReasonIdByText = (reasonText, issueReasons) => {
  if (!reasonText) return null
  const reasons = issueReasons || issueReasons.value
  const reason = reasons.find(r => r.reason_name === reasonText)
  return reason ? reason.id : null
}

// 根据 ID 查找问题原因文本
const findReasonTextById = (reasonId, issueReasons) => {
  if (!reasonId) return null
  const reasons = issueReasons || issueReasons.value
  const reason = reasons.find(r => r.id === reasonId)
  return reason ? reason.reason_name : null
}

// 处理数据，将问题原因映射到前端格式
const processTableData = (data, issueReasonsList) => {
  if (!data || !Array.isArray(data)) return []
  
  return data.map(item => {
    let issueReasonId = null
    let issueReasonText = null
    
    // 如果后端返回的是 issue_reason_id，直接使用
    if (item.issue_reason_id) {
      issueReasonId = item.issue_reason_id
      issueReasonText = findReasonTextById(item.issue_reason_id, issueReasonsList)
    } 
    // 如果后端返回的是 issue_reason（文本），尝试查找 ID
    else if (item.issue_reason) {
      issueReasonId = findReasonIdByText(item.issue_reason, issueReasonsList)
      issueReasonText = item.issue_reason
    }
    
    return {
      ...item,
      issue_reason_id: issueReasonId,
      issue_reason: issueReasonText,
      issue_status: item.issue_status || 'normal'
    }
  })
}

// 处理后的数据
const processedData = computed(() => processTableData(props.data, issueReasons.value))

// 处理问题原因变更
const handleIssueReasonChange = async (row, reasonId) => {
  const originalReasonId = row.issue_reason_id
  
  try {
    const response = await api.updateBarcodeIssueReason({
      barcode: row.barcode,
      issue_reason_id: reasonId,
      custom_reason: '',
      issue_status: row.issue_status
    })
    
    if (response.success) {
      ElMessage.success('问题原因已更新')
      
      // 更新当前行的显示数据
      if (reasonId) {
        const selectedReason = issueReasons.value.find(r => r.id === reasonId)
        if (selectedReason) {
          row.issue_reason = selectedReason.reason_name
          row.custom_reason = ''
        }
      } else {
        row.issue_reason = null
        row.custom_reason = ''
      }
      
      emit('issue-updated')
    } else {
      ElMessage.error(response.message || '更新失败')
      // 恢复原值
      row.issue_reason_id = originalReasonId
    }
  } catch (error) {
    ElMessage.error('更新失败')
    // 恢复原值
    row.issue_reason_id = originalReasonId
  }
}

// 处理问题状态变更
const handleIssueStatusChange = async (row, status) => {
  const originalStatus = row.issue_status
  
  try {
    const response = await api.updateBarcodeIssueReason({
      barcode: row.barcode,
      issue_reason_id: row.issue_reason_id,
      custom_reason: '',
      issue_status: status
    })
    
    if (response.success) {
      ElMessage.success('问题状态已更新')
      emit('issue-updated')
    } else {
      ElMessage.error(response.message || '更新失败')
      // 恢复原值
      row.issue_status = originalStatus
    }
  } catch (error) {
    ElMessage.error('更新失败')
    // 恢复原值
    row.issue_status = originalStatus
  }
}

// 分页数据
const currentPage = computed({
  get: () => props.pagination.currentPage,
  set: (value) => emit('page-change', value)
})

const pageSize = computed({
  get: () => props.pagination.pageSize,
  set: (value) => emit('size-change', value)
})

// 分页事件
const handleSizeChange = (size) => {
  pageSize.value = size
  emit('size-change', size)
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  emit('page-change', page)
}

// 导出功能
const handleExport = () => {
  const csvContent = [
    ['条码', '扫描次数', '设备数', '扫描时间', '设备IP', '维护人', '问题原因', '问题状态'].join(','),
    ...processedData.value.map(row => [
      row.barcode,
      row.scan_count,
      row.device_count,
      row.scan_time,
      row.devices || '未知',
      getMaintainer(row.barcode),
      row.issue_reason || '',
      row.issue_status
    ].join(','))
  ].join('\n')
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `条码统计_${dayjs().format('YYYY-MM-DD')}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

// 工具函数
const formatBarcode = (barcode) => {
  if (!barcode) return ''
  return barcode.length > 30 ? barcode.substring(0, 30) + '...' : barcode
}

const formatDateTime = (datetime) => {
  if (!datetime) return ''
  return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
}

const getCountType = (count) => {
  if (count >= 100) return 'danger'
  if (count >= 50) return 'warning'
  if (count >= 10) return 'primary'
  return 'success'
}

const getMaintainer = (barcode) => {
  const maintainerConfig = {
    "TEST_BARCODE_000": "张三",
    "TEST_BARCODE_001": "李四", 
    "TEST_BARCODE_002": "王五",
    "TEST_BARCODE_003": "赵六",
    "TEST_BARCODE_004": "钱七",
    "TEST_BARCODE_005": "孙八",
    "TEST_BARCODE_006": "周九",
    "TEST_BARCODE_007": "吴十",
    "TEST_BARCODE_008": "郑十一",
    "TEST_BARCODE_009": "王十二",
    "1234567890123": "张三",
    "9876543210987": "李四",
    "1112223334445": "王五",
    "5556667778889": "赵六",
    "9998887776665": "钱七",
    "4443332221110": "孙八",
    "7778889990001": "周九",
    "2223334445556": "吴十",
    "8889990001112": "郑十一",
    "3334445556667": "王十二"
  }
  
  return maintainerConfig[barcode] || '未分配'
}

// 组件挂载时加载问题原因
onMounted(() => {
  loadIssueReasons()
})

// 监听数据变化，处理数据映射
watch(() => props.data, (newData) => {
  if (newData && newData.length > 0) {
    // 数据更新时处理映射，不需要重新加载问题原因
    processedData.value
  }
}, { immediate: true })
</script>

<style scoped>
.table-card {
  margin-top: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.issue-reason-selector {
  display: flex;
  align-items: center;
}

.el-table .el-tag {
  margin-right: 4px;
}
</style>