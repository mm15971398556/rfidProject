<!-- src/components/SearchForm.vue -->
<template>
  <el-card class="search-card" :body-style="{ padding: '20px' }">
    <el-form :inline="true" :model="form" class="search-form">
      <el-form-item label="年份">
        <el-select 
          v-model="form.year" 
          placeholder="选择年份" 
          clearable
          style="width: 140px"
        >
          <el-option 
            v-for="y in years" 
            :key="y" 
            :label="y" 
            :value="y"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="月份">
        <el-select 
          v-model="form.month" 
          placeholder="选择月份" 
          clearable
          style="width: 140px"
        >
          <el-option 
            v-for="m in 12" 
            :key="m" 
            :label="m" 
            :value="m"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="日期">
        <el-select 
          v-model="form.day" 
          placeholder="选择日期" 
          clearable
          style="width: 140px"
        >
          <el-option 
            v-for="d in daysInMonth" 
            :key="d" 
            :label="d" 
            :value="d"
          />
        </el-select>
      </el-form-item>
      
      <el-form-item label="条码">
        <el-input 
          v-model="form.barcode" 
          placeholder="输入条码关键词" 
          clearable
          style="width: 280px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </el-form-item>
      
      <el-form-item>
        <el-button 
          type="primary" 
          @click="handleSearch"
          :loading="loading"
        >
          <el-icon><Search /></el-icon> 查询
        </el-button>
        <el-button @click="handleReset">
          <el-icon><Refresh /></el-icon> 重置
        </el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['search', 'reset'])

// 年份选项
const years = computed(() => {
  const currentYear = new Date().getFullYear()
  return Array.from({ length: 5 }, (_, i) => (currentYear - i).toString())
})

// 表单数据
const form = ref({
  year: new Date().getFullYear().toString(),
  month: (new Date().getMonth() + 1).toString(),
  day: '',
  barcode: ''
})

// 计算当月天数
const daysInMonth = computed(() => {
  if (!form.value.year || !form.value.month) return []
  const year = parseInt(form.value.year)
  const month = parseInt(form.value.month)
  return new Date(year, month, 0).getDate()
})

// 搜索
const handleSearch = () => {
  emit('search', { ...form.value })
}

// 重置
const handleReset = () => {
  form.value = {
    year: new Date().getFullYear().toString(),
    month: (new Date().getMonth() + 1).toString(),
    day: '',
    barcode: ''
  }
  emit('reset')
}

// 监听年月变化，自动清空日期
watch(
  () => [form.value.year, form.value.month],
  () => {
    form.value.day = ''
  }
)
</script>