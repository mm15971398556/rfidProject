<!-- src/components/StatCards.vue -->
<template>
  <el-row :gutter="20" class="stat-cards">
    <el-col :xs="24" :sm="12" :md="6" v-for="card in cards" :key="card.label">
      <el-card class="stat-card" :body-style="{ padding: '0' }">
        <div class="stat-content">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">
            <el-skeleton :loading="loading" :rows="1" animated>
              <template #default>
                {{ card.value }}
                <span v-if="card.unit" class="stat-unit">{{ card.unit }}</span>
              </template>
            </el-skeleton>
          </div>
          <div v-if="card.tip" class="stat-tip">{{ card.tip }}</div>
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const cards = computed(() => [
  {
    label: '总条码数',
    value: props.stats.totalBarcodes || 0,
    tip: '去重后的条码数量'
  },
  {
    label: '总扫描次数',
    value: props.stats.totalScans || 0,
    tip: '所有条码的扫描总次数'
  },
  {
    label: '设备数',
    value: props.stats.totalDevices || 0,
    unit: '台',
    tip: '扫描设备的数量'
  },
  {
    label: '扫描最多的条码',
    value: props.stats.topBarcode || '-',
    tip: '当前查询范围内扫描次数最多的条码'
  }
])
</script>

<style scoped>
.stat-cards {
  margin-top: 20px;
  margin-bottom: 20px;
}

.stat-content {
  padding: 20px;
}

.stat-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}
</style>