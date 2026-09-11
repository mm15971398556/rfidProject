<!-- src/views/IssueReasons.vue -->
<template>
  <div class="issue-reasons-container">
    <el-card class="main-card">
      <template #header>
        <div class="page-header">
          <h2>
            <el-icon><Setting /></el-icon>
            问题原因管理
          </h2>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreate">
              <el-icon><Plus /></el-icon>
              新增原因
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索和筛选 -->
      <div class="filter-container">
        <el-form :model="filterForm" inline>
          <el-form-item label="原因名称">
            <el-input 
              v-model="filterForm.reason_name" 
              placeholder="输入原因名称" 
              clearable
              style="width: 200px"
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="状态">
            <el-select 
              v-model="filterForm.is_active" 
              placeholder="请选择状态" 
              clearable 
              style="width: 140px"
              @change="handleSearch"
            >
              <el-option label="全部" value="all" />
              <el-option label="启用" value="true" />
              <el-option label="禁用" value="false" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="分类">
            <el-select 
              v-model="filterForm.category" 
              placeholder="请选择分类" 
              clearable
              style="width: 140px"
              @change="handleSearch"
            >
              <el-option label="技术问题" value="technical" />
              <el-option label="设备问题" value="equipment" />
              <el-option label="操作问题" value="operation" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
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
        <el-table-column prop="reason_code" label="原因代码" width="120" />
        <el-table-column prop="reason_name" label="原因名称" min-width="150" />
        <el-table-column prop="description" label="详细描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="sort_order" label="排序" width="80" sortable />
        
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_time" label="创建时间" width="180" />
        <el-table-column prop="updated_time" label="更新时间" width="180" />
        
        <el-table-column label="操作" width="200" fixed="right">
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
      width="600px"
      :before-close="handleDialogClose"
    >
      <el-form 
        :model="form" 
        :rules="rules" 
        ref="formRef"
        label-width="100px"
      >
        <el-form-item label="原因代码" prop="reason_code">
          <el-input 
            v-model="form.reason_code" 
            placeholder="请输入原因代码" 
            maxlength="50"
          />
        </el-form-item>
        
        <el-form-item label="原因名称" prop="reason_name">
          <el-input 
            v-model="form.reason_name" 
            placeholder="请输入原因名称" 
            maxlength="100"
          />
        </el-form-item>
        
        <el-form-item label="详细描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入详细描述"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item label="分类">
          <el-input 
            v-model="form.category" 
            placeholder="请输入分类" 
            maxlength="50"
          />
        </el-form-item>
        
        <el-form-item label="排序">
          <el-input-number 
            v-model="form.sort_order" 
            :min="0" 
            :max="999"
            controls-position="right"
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
        <el-button @click="handleDialogClose">取消</el-button>
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
import { Setting, Plus } from '@element-plus/icons-vue'
import api from '../api'

// 响应式数据
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()

const filterForm = reactive({
  reason_name: '',
  is_active: 'all',
  category: ''
})

const form = reactive({
  id: null,
  reason_code: '',
  reason_name: '',
  description: '',
  category: '',
  sort_order: 0,
  is_active: true
})

const tableData = ref([])
const categories = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogTitle = computed(() => form.id ? '编辑问题原因' : '新增问题原因')

// 表单验证规则
const rules = {
  reason_code: [
    { required: true, message: '请输入原因代码', trigger: 'blur' }
  ],
  reason_name: [
    { required: true, message: '请输入原因名称', trigger: 'blur' }
  ]
}

// 生命周期
onMounted(() => {
  loadData()
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      pageSize: pageSize.value
    }
    
    if (filterForm.is_active && filterForm.is_active !== '' && filterForm.is_active !== 'all') {
      params.is_active = filterForm.is_active
    }
    
    const response = await api.getIssueReasons(params)
    if (response.success) {
      // 转换 is_active 为布尔值
      tableData.value = Array.isArray(response.data) 
        ? response.data.map(item => ({
            ...item,
            is_active: item.is_active === 1 || item.is_active === true
          }))
        : []
      total.value = response.pagination ? response.pagination.total : (Array.isArray(response.data) ? response.data.length : 0)
    }
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

// 重置
const handleReset = () => {
  filterForm.is_active = 'all'
  handleSearch()
}

// 新增
const handleCreate = () => {
  Object.assign(form, {
    id: null,
    reason_code: '',
    reason_name: '',
    description: '',
    category: '',
    sort_order: 0,
    is_active: true
  })
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  form.id = row.id
  form.reason_code = row.reason_code
  form.reason_name = row.reason_name
  form.description = row.description
  form.category = row.category
  form.sort_order = row.sort_order
  form.is_active = Boolean(row.is_active)
  dialogVisible.value = true
}

// 切换状态
const handleToggleStatus = async (row) => {
  try {
    const isActive = row.is_active === 1 || row.is_active === true
    await ElMessageBox.confirm(
      `确定要${isActive ? '禁用' : '启用'}该问题原因吗？`,
      '提示',
      { type: 'warning' }
    )
    
    const response = await api.updateIssueReason(row.id, { is_active: !isActive })
    if (response.success) {
      ElMessage.success('操作成功')
      // 强制刷新当前筛选状态的数据
      loadData()
    } else {
      ElMessage.error(response.message || '操作失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该问题原因吗？', '提示', { type: 'warning' })
    
    const response = await api.deleteIssueReason(row.id)
    if (response.success) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate()
  if (!valid) return
  
  submitting.value = true
  try {
    let response
    if (form.id) {
      response = await api.updateIssueReason(form.id, form)
    } else {
      response = await api.createIssueReason(form)
    }
    
    if (response.success) {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      loadData()
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

// 关闭对话框
const handleDialogClose = () => {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

// 分页处理
const handleSizeChange = (val) => {
  pageSize.value = val
  loadData()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  loadData()
}
</script>

<style scoped>
.issue-reasons-container {
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