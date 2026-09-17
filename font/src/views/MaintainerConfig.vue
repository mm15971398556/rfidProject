<!-- src/views/MaintainerConfig.vue -->
<template>
  <div class="maintainer-config-container">
    <el-card class="main-card">
      <template #header>
        <div class="page-header">
          <h2>
            <el-icon><User /></el-icon>
            条码维护人配置
          </h2>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreate">
              <el-icon><Plus /></el-icon>
              新增映射
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-container">
        <el-form :model="filterForm" inline>
          <el-form-item label="关键词">
            <el-input 
              v-model="filterForm.keyword" 
              placeholder="输入条码或维护人" 
              clearable
              style="width: 240px"
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="状态">
            <el-select 
              v-model="filterForm.is_active" 
              style="width: 140px"
              @change="handleSearch"
            >
              <el-option label="全部" value="all" />
              <el-option label="启用" value="true" />
              <el-option label="禁用" value="false" />
            </el-select>
          </el-form-item>

          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form>
      </div>

      <!-- 数据表格 -->
      <el-table 
        :data="tableData" 
        v-loading="loading"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="barcode" label="条码" min-width="240" show-overflow-tooltip />
        <el-table-column prop="maintainer_name" label="维护人" width="160" />
        
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_time" label="创建时间" width="180" />
        <el-table-column prop="updated_time" label="更新时间" width="180" />
        
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button 
              type="warning" 
              link 
              size="small" 
              @click="handleToggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
    >
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef"
        label-width="100px"
      >
        <el-form-item label="条码" prop="barcode">
          <el-input 
            v-model="form.barcode" 
            placeholder="请输入条码（如 TEST_BARCODE_001 或 RFID EPC hex）" 
            maxlength="200"
            :disabled="!!form.id"
          />
        </el-form-item>
        
        <el-form-item label="维护人" prop="maintainer_name">
          <el-input 
            v-model="form.maintainer_name" 
            placeholder="请输入维护人姓名" 
            maxlength="100"
          />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch
            v-model="form.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Plus } from '@element-plus/icons-vue'
import { maintainerApi } from '../api'

const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()

const filterForm = reactive({
  keyword: '',
  is_active: 'all'
})

const form = reactive({
  id: null,
  barcode: '',
  maintainer_name: '',
  is_active: true
})

const tableData = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogTitle = computed(() => form.id ? '编辑维护人映射' : '新增维护人映射')

const rules = {
  barcode: [{ required: true, message: '请输入条码', trigger: 'blur' }],
  maintainer_name: [{ required: true, message: '请输入维护人', trigger: 'blur' }]
}

onMounted(() => {
  loadData()
})

const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value,
      is_active: filterForm.is_active
    }
    if (filterForm.keyword.trim()) {
      params.keyword = filterForm.keyword.trim()
    }

    const response = await maintainerApi.getList(params)
    if (response.success) {
      tableData.value = Array.isArray(response.data)
        ? response.data.map(item => ({
            ...item,
            is_active: item.is_active === 1 || item.is_active === true
          }))
        : []
      total.value = response.pagination ? response.pagination.total : 0
    }
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

const handleReset = () => {
  filterForm.keyword = ''
  filterForm.is_active = 'all'
  handleSearch()
}

const handleCreate = () => {
  Object.assign(form, { id: null, barcode: '', maintainer_name: '', is_active: true })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  Object.assign(form, {
    id: row.id,
    barcode: row.barcode,
    maintainer_name: row.maintainer_name,
    is_active: Boolean(row.is_active)
  })
  dialogVisible.value = true
}

const handleToggleStatus = async (row) => {
  try {
    const isActive = row.is_active === 1 || row.is_active === true
    await ElMessageBox.confirm(
      `确定要${isActive ? '禁用' : '启用'}这条映射吗？`,
      '提示', { type: 'warning' }
    )
    const response = await maintainerApi.update(row.id, { is_active: !isActive })
    if (response.success) {
      ElMessage.success('操作成功')
      loadData()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这条映射吗？', '提示', { type: 'warning' })
    const response = await maintainerApi.delete(row.id)
    if (response.success) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate()
  if (!valid) return

  submitting.value = true
  try {
    let response
    if (form.id) {
      response = await maintainerApi.update(form.id, {
        maintainer_name: form.maintainer_name,
        is_active: form.is_active
      })
    } else {
      response = await maintainerApi.create({
        barcode: form.barcode,
        maintainer_name: form.maintainer_name,
        is_active: form.is_active
      })
    }

    if (response.success) {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    } else {
      ElMessage.error(response.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

const handleSizeChange = () => loadData()
const handleCurrentChange = () => loadData()
</script>

<style scoped>
.maintainer-config-container {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-container {
  margin-bottom: 20px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
:deep(.el-table) {
  margin-top: 10px;
}
:deep(.el-table__header th) {
  background-color: #f5f7fa;
  font-weight: 600;
}
</style>
