<template>
  <div class="page">
    <el-tabs v-model="tab" class="surface tabs">
      <el-tab-pane label="预算 / 借款" name="budget">
        <el-form label-width="120px" class="form">
          <el-form-item label="类型">
            <el-radio-group v-model="budget.kind">
              <el-radio-button value="budget">预算申请</el-radio-button>
              <el-radio-button value="loan">借款说明</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="竞赛名称"><el-input v-model="budget.competition_name" /></el-form-item>
          <el-form-item label="人数"><el-input-number v-model="budget.people" :min="0" /></el-form-item>
          <el-form-item label="地点"><el-input v-model="budget.location" placeholder="本校/省内/外省" /></el-form-item>
          <el-form-item label="报名费/人"><el-input-number v-model="budget.registration_fee" :min="0" :step="50" /></el-form-item>
          <el-form-item label="交通/人"><el-input-number v-model="budget.transport_per_person" :min="0" :step="50" /></el-form-item>
          <el-form-item label="住宿单价/晚"><el-input-number v-model="budget.lodging_per_person_night" :min="0" :step="50" /></el-form-item>
          <el-form-item label="住宿晚数"><el-input-number v-model="budget.nights" :min="0" /></el-form-item>
          <el-form-item label="市内交通"><el-input-number v-model="budget.local_transport" :min="0" /></el-form-item>
          <el-form-item label="其他"><el-input-number v-model="budget.other" :min="0" /></el-form-item>
          <el-form-item v-if="budget.kind === 'loan'" label="预算文号"><el-input v-model="budget.budget_ref" /></el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="genBudget">生成草稿</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="报销检查" name="reimburse">
        <el-form label-width="120px" class="form">
          <el-form-item label="竞赛名称"><el-input v-model="reimburse.competition_name" /></el-form-item>
          <el-form-item label="已有材料">
            <el-checkbox-group v-model="reimburse.provided_materials">
              <el-checkbox label="发票原件" />
              <el-checkbox label="行程单据" />
              <el-checkbox label="参赛证明（通知/参赛证）" />
              <el-checkbox label="批准预算表" />
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="备注"><el-input v-model="reimburse.note" type="textarea" /></el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="genReimburse">生成整理说明</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="备赛计划" name="prep">
        <el-input v-model="prepQuestion" type="textarea" :rows="4" placeholder="例如：为 2026 程序设计竞赛生成 4 周备赛计划" />
        <div class="mt">
          <el-button type="primary" :loading="loading" @click="genPrep">生成计划</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="材料初审" name="review">
        <el-form label-width="120px">
          <el-form-item label="材料文件"><input type="file" @change="onReviewFile" /></el-form-item>
          <el-form-item label="材料清单"><el-input v-model="reviewMaterials" placeholder="逗号分隔，可留空用默认清单" /></el-form-item>
          <el-form-item label="额外说明"><el-input v-model="reviewQuestion" type="textarea" /></el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" :disabled="!reviewFile" @click="genReview">开始初审</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="历史草稿" name="history">
        <el-button class="mb" @click="loadDrafts">刷新</el-button>
        <h4>财务草稿</h4>
        <el-table :data="drafts.finance" size="small">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="kind" label="类型" width="110" />
          <el-table-column label="下载" width="100">
            <template #default="{ row }">
              <a :href="row.download_url" target="_blank">下载</a>
            </template>
          </el-table-column>
        </el-table>
        <h4 class="mt">写作草稿</h4>
        <el-table :data="drafts.workspace" size="small">
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="kind" label="类型" width="110" />
          <el-table-column label="下载" width="100">
            <template #default="{ row }">
              <a :href="row.download_url" target="_blank">下载</a>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <section v-if="preview" class="surface preview">
      <div class="preview-head">
        <h3>生成结果</h3>
        <a v-if="downloadUrl" :href="downloadUrl" target="_blank">下载文件</a>
      </div>
      <pre>{{ preview }}</pre>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  createBudgetDraft,
  createReimbursement,
  createPrepPlan,
  listWorkspaceDrafts,
  reviewMaterial,
} from "../api/client";

const tab = ref("budget");
const loading = ref(false);
const preview = ref("");
const downloadUrl = ref("");
const drafts = reactive({ finance: [], workspace: [] });

const budget = reactive({
  kind: "budget",
  competition_name: "程序设计竞赛",
  people: 3,
  location: "外省",
  registration_fee: 0,
  transport_per_person: 400,
  lodging_per_person_night: 200,
  nights: 2,
  local_transport: 100,
  other: 0,
  other_note: "",
  budget_ref: "",
});

const reimburse = reactive({
  competition_name: "中国大学生计算机设计大赛",
  provided_materials: ["发票原件"],
  note: "",
});

const prepQuestion = ref("请为软件工程大二同学生成 2026 程序设计竞赛备赛计划");
const reviewFile = ref(null);
const reviewMaterials = ref("报名表,学生证,团队分工说明");
const reviewQuestion = ref("请初审并给出修改建议与答辩题");

function onReviewFile(e) {
  reviewFile.value = e.target.files?.[0] || null;
}

async function loadDrafts() {
  const data = await listWorkspaceDrafts();
  drafts.finance = data.finance || [];
  drafts.workspace = data.workspace || [];
}

async function genBudget() {
  loading.value = true;
  try {
    const res = await createBudgetDraft({ ...budget });
    preview.value = res.content_md;
    downloadUrl.value = res.download_url;
    ElMessage.success("已生成");
    await loadDrafts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    loading.value = false;
  }
}

async function genReimburse() {
  loading.value = true;
  try {
    const res = await createReimbursement({ ...reimburse });
    preview.value = res.content_md;
    downloadUrl.value = res.download_url;
    ElMessage.success(res.check?.ok ? "材料齐全" : "仍有缺失项");
    await loadDrafts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    loading.value = false;
  }
}

async function genPrep() {
  loading.value = true;
  try {
    const res = await createPrepPlan(prepQuestion.value);
    preview.value = res.content_md;
    downloadUrl.value = res.download_url;
    ElMessage.success("计划已生成");
    await loadDrafts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "生成失败");
  } finally {
    loading.value = false;
  }
}

async function genReview() {
  if (!reviewFile.value) return;
  loading.value = true;
  try {
    const fd = new FormData();
    fd.append("file", reviewFile.value);
    fd.append("competition_materials", reviewMaterials.value);
    fd.append("question", reviewQuestion.value);
    const res = await reviewMaterial(fd);
    preview.value = res.content_md;
    downloadUrl.value = res.download_url;
    ElMessage.success("初审完成");
    await loadDrafts();
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || "初审失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadDrafts);
</script>

<style scoped>
.tabs {
  padding: 0.75rem 1rem 1rem;
}

.form {
  max-width: 640px;
}

.mt {
  margin-top: 0.85rem;
}

.mb {
  margin-bottom: 0.75rem;
}

.preview {
  margin-top: 1rem;
  padding: 1rem 1.15rem;
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview h3 {
  margin: 0;
  font-family: var(--font-display);
}

.preview pre {
  white-space: pre-wrap;
  line-height: 1.55;
  color: var(--ink);
  background: #f7faf9;
  border-radius: 12px;
  padding: 0.9rem;
  border: 1px solid var(--line);
}
</style>
