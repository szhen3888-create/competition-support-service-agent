<template>
  <div class="grid">
    <section class="surface upload-card">
      <h3>导入资料</h3>
      <p class="desc">支持 PDF / Word / Excel / Markdown。入库后可在对话中引用原文。</p>
      <el-form label-position="top">
        <el-form-item label="文件">
          <input type="file" @change="onFile" />
        </el-form-item>
        <div class="two">
          <el-form-item label="标题">
            <el-input v-model="form.title" placeholder="可选" />
          </el-form-item>
          <el-form-item label="竞赛">
            <el-input v-model="form.competition" placeholder="如：程序设计竞赛" />
          </el-form-item>
        </div>
        <div class="two">
          <el-form-item label="年份">
            <el-input v-model="form.year" placeholder="2026" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="form.doc_type" style="width: 100%">
              <el-option label="通知" value="通知" />
              <el-option label="规程" value="规程" />
              <el-option label="政策" value="政策" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
        </div>
        <el-button type="primary" :loading="uploading" :disabled="!file" @click="upload">
          上传并入库
        </el-button>
      </el-form>
      <div class="stat-row">
        <div><b>{{ stats.documents || 0 }}</b><span>文档</span></div>
        <div><b>{{ stats.active_documents || 0 }}</b><span>启用</span></div>
        <div><b>{{ stats.chunks || 0 }}</b><span>分块</span></div>
      </div>
    </section>

    <section class="surface table-card">
      <div class="head">
        <h3>已入库文档</h3>
        <el-button @click="refresh">刷新</el-button>
      </div>
      <el-table :data="items" height="100%" empty-text="暂无文档">
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="competition" label="竞赛" width="130" />
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column prop="doc_type" label="类型" width="80" />
        <el-table-column prop="chunk_count" label="分块" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.active ? 'success' : 'info'" round size="small">
              {{ row.active ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="toggle(row)">
              {{ row.active ? "停用" : "启用" }}
            </el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  deleteDocument,
  knowledgeStats,
  listDocuments,
  setDocumentActive,
  uploadDocument,
} from "../api/client";

const items = ref([]);
const stats = ref({});
const file = ref(null);
const uploading = ref(false);
const form = reactive({ title: "", competition: "", year: "", doc_type: "通知" });

function onFile(e) {
  file.value = e.target.files?.[0] || null;
}

async function refresh() {
  const [docs, st] = await Promise.all([listDocuments(), knowledgeStats()]);
  items.value = docs.items || [];
  stats.value = st || {};
}

async function upload() {
  uploading.value = true;
  try {
    const fd = new FormData();
    fd.append("file", file.value);
    fd.append("title", form.title);
    fd.append("competition", form.competition);
    fd.append("year", form.year);
    fd.append("doc_type", form.doc_type);
    await uploadDocument(fd);
    ElMessage.success("入库成功");
    file.value = null;
    await refresh();
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || "上传失败");
  } finally {
    uploading.value = false;
  }
}

async function toggle(row) {
  await setDocumentActive(row.id, !row.active);
  await refresh();
}

async function remove(row) {
  await ElMessageBox.confirm(`删除「${row.title}」？`, "确认", { type: "warning" });
  await deleteDocument(row.id);
  await refresh();
}

onMounted(async () => {
  try {
    await refresh();
  } catch {
    ElMessage.error("加载失败，请确认后端已启动");
  }
});
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 1rem;
  min-height: calc(100vh - 120px);
}

.upload-card,
.table-card {
  padding: 1.15rem 1.2rem;
}

.table-card {
  display: flex;
  flex-direction: column;
  min-height: 560px;
}

h3 {
  margin: 0;
  font-family: var(--font-display);
}

.desc {
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.5;
}

.two {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
}

.stat-row {
  margin-top: 1.2rem;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.stat-row div {
  background: var(--accent-soft);
  border-radius: 12px;
  padding: 0.75rem;
  text-align: center;
}

.stat-row b {
  display: block;
  font-size: 1.25rem;
  color: var(--accent);
}

.stat-row span {
  color: var(--muted);
  font-size: 0.75rem;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
