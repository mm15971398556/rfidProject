<!-- src/components/Charts.vue -->
<template>
  <el-card>
    <template #header>
      <div class="chart-header">
        <span>{{ title }}</span>
        <el-tag v-if="loading" size="small" type="info">加载中...</el-tag>
      </div>
    </template>
    
    <div class="chart-container">
      <div 
        ref="chartRef" 
        class="chart"
        :style="{ height: height }"
      ></div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'pie' // pie, bar, line
  },
  data: {
    type: Object,
    default: () => ({ xAxis: [], series: [] })
  },
  height: {
    type: String,
    default: '300px'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartRef = ref(null)
let chart = null

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  // 根据图表类型设置不同的配置
  let option = {}
  
  if (props.type === 'pie') {
    // 饼图配置
    option = {
      title: {
        show: false
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle'
      },
      series: (props.data.series || []).map(s => ({
        name: s.name || '',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c} ({d}%)',
          position: 'outside',
          alignTo: 'labelLine',
          bleedMargin: 5
        },
        labelLine: {
          show: true,
          length: 20,
          length2: 30,
          smooth: 0.2
        },
        emphasis: {
          label: {
            show: true,
            fontSize: '16',
            fontWeight: 'bold'
          }
        },
        data: s.data || []
      }))
    }
  } else {
    // 柱状图和折线图配置
    option = {
      title: {
        show: false
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        show: props.type !== 'bar',
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '5%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: props.data.xAxis || [],
        axisLabel: {
          rotate: props.data.xAxis?.length > 8 ? 30 : 0,
          interval: 0
        }
      },
      yAxis: {
        type: 'value'
      },
      series: (props.data.series || []).map(s => ({
        name: s.name || '',
        type: props.type || 'bar',  // 默认使用bar类型
        data: s.data || [],
        itemStyle: {
          color: props.type === 'bar' 
            ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#83bff6' },
                { offset: 0.5, color: '#188df0' },
                { offset: 1, color: '#188df0' }
              ])
            : undefined
        },
        smooth: true,
        symbol: 'circle',
        symbolSize: 8
      }))
    }
  }
  
  chart.setOption(option)
  
  // 响应式
  window.addEventListener('resize', handleResize)
}

// 更新图表
const updateChart = () => {
  if (!chart) return
  
  let option = {}
  
  if (props.type === 'pie') {
    option = {
      series: (props.data.series || []).map(s => ({
        name: s.name || '',
        type: 'pie',  // 明确指定饼图类型
        data: s.data || []
      }))
    }
  } else {
    option = {
      xAxis: {
        data: props.data.xAxis || []
      },
      series: (props.data.series || []).map(s => ({
        name: s.name || '',
        type: props.type || 'bar',  // 添加类型，防止undefined
        data: s.data || []
      }))
    }
  }
  
  chart.setOption(option)
}

// 处理窗口大小变化
const handleResize = () => {
  chart?.resize()
}

// 监听数据变化
watch(
  () => props.data,
  () => {
    updateChart()
  },
  { deep: true }
)

// 监听类型变化
watch(
  () => props.type,
  () => {
    initChart()
  }
)

onMounted(() => {
  initChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  width: 100%;
  position: relative;
}

.chart {
  width: 100%;
}
</style>