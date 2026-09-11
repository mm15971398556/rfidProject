<!-- src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <!-- 搜索表单 -->
    <SearchForm 
      :loading="loading"
      @search="handleSearch"
      @reset="handleReset"
    />
    
    <!-- 统计卡片 -->
    <StatCards 
      :stats="stats"
      :loading="loading"
    />
    
    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :sm="24" :md="12">
        <Charts
          title="问题原因分布"
          type="pie"
          :data="issueReasonChartData"
          :loading="chartLoading"
        />
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <Charts
          title="人员出现次数分布"
          type="pie"
          :data="personnelCountChartData"
          :loading="chartLoading"
        />
      </el-col>
    </el-row>
    
    <!-- 数据表格 -->
    <BarcodeTable
      :data="tableData"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
      @view-detail="handleViewDetail"
      @issue-updated="handleIssueUpdated"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SearchForm from '../components/SearchForm.vue'
import StatCards from '../components/StatCards.vue'
import Charts from '../components/Charts.vue'
import BarcodeTable from '../components/BarcodeTable.vue'
import { statsApi } from '../api'

// 加载状态
const loading = ref(false)
const chartLoading = ref(false)

// 统计信息
const stats = reactive({
  totalBarcodes: 0,
  totalScans: 0,
  totalDevices: 0,
  topBarcode: '-'
})

// 表格数据
const tableData = ref([])

// 分页
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
  totalPages: 0
})

// 图表数据
const barcodeChartData = ref({
  xAxis: [],
  series: []
})

const dateChartData = ref({
  xAxis: [],
  series: []
})

// 新的图表数据
const issueReasonChartData = ref({
  xAxis: [],
  series: []
})

const maintainerChartData = ref({
  xAxis: [],
  series: []
})

const personnelCountChartData = ref({
  xAxis: [],
  series: []
})

// 搜索参数
const searchParams = reactive({
  year: new Date().getFullYear().toString(),
  month: (new Date().getMonth() + 1).toString(),
  day: '',
  barcode: ''
})

// 处理搜索
const handleSearch = async (params) => {
  Object.assign(searchParams, params)
  pagination.currentPage = 1  // 重置到第一页
  await fetchData()
}

// 处理重置
const handleReset = () => {
  searchParams.year = new Date().getFullYear().toString()
  searchParams.month = (new Date().getMonth() + 1).toString()
  searchParams.day = ''
  searchParams.barcode = ''
  pagination.currentPage = 1
  fetchData()
}

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    // 获取条码统计数据（带分页）
    const result = await statsApi.getBarcodeStats({
      year: searchParams.year,
      month: searchParams.month,
      day: searchParams.day,
      barcode: searchParams.barcode,
      page: pagination.currentPage,
      pageSize: pagination.pageSize
    })
    
    if (result.success) {
      // 更新表格数据
      tableData.value = result.data
      
      // 更新分页信息
      pagination.total = result.pagination.total
      pagination.totalPages = result.pagination.totalPages
      
      // 计算统计信息（基于单条扫描记录）
      stats.totalBarcodes = result.pagination.uniqueBarcodes  // 使用后端返回的去重条码数
      stats.totalScans = result.pagination.total              // 总扫描次数等于总记录数
      
      // 计算设备数（基于单条记录）
      const devices = new Set()
      result.data.forEach(item => {
        if (item.devices) {
          devices.add(item.devices)  // 每条记录对应一个设备IP
        }
      })
      stats.totalDevices = devices.size
      
      // 计算最频繁扫描的条码
      const barcodeCounts = {}
      result.data.forEach(item => {
        barcodeCounts[item.barcode] = (barcodeCounts[item.barcode] || 0) + 1
      })
      
      if (Object.keys(barcodeCounts).length > 0) {
        const topBarcode = Object.keys(barcodeCounts).reduce((a, b) => 
          barcodeCounts[a] > barcodeCounts[b] ? a : b
        )
        stats.topBarcode = topBarcode
      } else {
        stats.topBarcode = '-'
      }
      
      // 更新图表数据（使用热门条码API）
      await fetchTopBarcodes()
      
      // 更新新的图表数据
      updateNewCharts(result.data)
    }
  } catch (error) {
    ElMessage.error('获取数据失败：' + error.message)
  } finally {
    loading.value = false
  }
  
  // 获取日期统计数据
  fetchDateStats()
}

// 获取热门条码
const fetchTopBarcodes = async () => {
  try {
    const result = await statsApi.getTopBarcodes(10)
    if (result.success) {
      updateBarcodeChart(result.data)
    }
  } catch (error) {
    console.error('获取热门条码失败:', error)
  }
}

// 获取日期统计
const fetchDateStats = async () => {
  chartLoading.value = true
  try {
    const result = await statsApi.getDateStats({
      year: searchParams.year,
      month: searchParams.month
    })
    
    if (result.success) {
      updateDateChart(result.data)
    }
  } catch (error) {
    console.error('获取日期统计失败:', error)
  } finally {
    chartLoading.value = false
  }
}

// 更新条码图表
const updateBarcodeChart = (data) => {
  barcodeChartData.value = {
    xAxis: data.map(item => 
      item.barcode.length > 15 ? item.barcode.substring(0, 15) + '...' : item.barcode
    ),
    series: [
      {
        name: '扫描次数',
        data: data.map(item => item.scan_count)
      }
    ]
  }
}

// 更新日期图表
const updateDateChart = (data) => {
  dateChartData.value = {
    xAxis: data.map(item => item.scan_date || item.scan_month),
    series: [
      {
        name: '条码数',
        data: data.map(item => item.unique_barcodes)
      },
      {
        name: '扫描次数',
        data: data.map(item => item.total_scans)
      },
      {
        name: '设备数',
        data: data.map(item => item.unique_devices)
      }
    ]
  }
}

// 分页处理
const handlePageChange = (page) => {
  pagination.currentPage = page
  fetchData()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchData()
}

// 查看条码详情
const handleViewDetail = (barcode) => {
  searchParams.barcode = barcode
  pagination.currentPage = 1
  fetchData()
}

// 问题原因更新后重新获取数据
const handleIssueUpdated = () => {
  fetchData()
}

// 监听年月变化，自动更新日期图表
watch(
  () => [searchParams.year, searchParams.month],
  () => {
    fetchDateStats()
  }
)

// 更新新的图表数据
const updateNewCharts = (data) => {
  // 导入维护人员配置
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
  
  // 1. 问题原因分布饼图 - 基于单条数据统计
  const issueReasonCounts = {}
  data.forEach(item => {
    if (item.issue_reason) {
      issueReasonCounts[item.issue_reason] = (issueReasonCounts[item.issue_reason] || 0) + 1
    }
  })
  
  issueReasonChartData.value = {
    xAxis: Object.keys(issueReasonCounts),
    series: [
      {
        name: '问题原因分布',
        data: Object.keys(issueReasonCounts).map(reason => ({
          name: reason,
          value: issueReasonCounts[reason]
        }))
      }
    ]
  }
  
  // 2. 维护人员分布饼图 - 基于单条数据统计
  const maintainerCounts = {}
  data.forEach(item => {
    const maintainer = maintainerConfig[item.barcode] || '未分配'
    maintainerCounts[maintainer] = (maintainerCounts[maintainer] || 0) + 1
  })
  
  maintainerChartData.value = {
    xAxis: Object.keys(maintainerCounts),
    series: [
      {
        name: '维护人员分布',
        data: Object.keys(maintainerCounts).map(person => ({
          name: person,
          value: maintainerCounts[person]
        }))
      }
    ]
  }
  
  // 3. 人员出现次数分布饼图 - 基于单条数据统计
  personnelCountChartData.value = {
    xAxis: Object.keys(maintainerCounts),
    series: [
      {
        name: '人员出现次数分布',
        data: Object.keys(maintainerCounts).map(person => ({
          name: person,
          value: maintainerCounts[person]
        }))
      }
    ]
  }
}

// 初始化
onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.chart-row {
  margin-top: 20px;
  margin-bottom: 20px;
}
</style>