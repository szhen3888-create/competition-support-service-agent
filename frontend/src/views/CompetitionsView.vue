<template>
  <div class="page">
    <el-tabs v-model="tab" class="surface tabs">
      <el-tab-pane label="竞赛列表" name="comp">
        <div class="toolbar">
          <el-input v-model="q" placeholder="搜索竞赛名称" style="width: 220px" clearable @change="loadComps" />
          <el-button type="primary" @click="openComp()">新增竞赛</el-button>
        </div>
        <el-table :data="comps" stripe>
          <el-table-column prop="name" label="名称" min-width="160" />
          <el-table-column prop="year" label="年份" width="80" />
          <el-table-column prop="level" label="级别" width="90" />
          <el-table-column prop="category" label="类别" width="110" />
          <el-table-column prop="major_tags" label="面向专业" min-width="140" />
          <el-table-column prop="status" label="状态" width="90" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openComp(row)">编辑</el-button>
              <el-button link type="danger" @click="removeComp(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="参赛 / 获奖" name="part">
        <div class="toolbar">
          <el-input v-model="major" placeholder="专业筛选" style="width: 160px" clearable @change="loadParts" />
          <el-button type="primary" @click="openPart()">新增记录</el-button>
        </div>
        <el-table :data="parts" stripe>
          <el-table-column prop="year" label="年" width="70" />
          <el-table-column prop="competition_name" label="竞赛" min-width="140" />
          <el-table-column prop="student_name" label="学生" width="90" />
          <el-table-column prop="major" label="专业" width="120" />
          <el-table-column prop="instructor" label="指导教师" width="100" />
          <el-table-column prop="award_level" label="奖项" width="90" />
          <el-table-column prop="project_title" label="项目" min-width="140" />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="danger" @click="removePart(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="compVisible" :title="compForm.id ? '编辑竞赛' : '新增竞赛'" width="640px">
      <el-form label-width="96px">
        <el-form-item label="名称"><el-input v-model="compForm.name" /></el-form-item>
        <el-form-item label="年份"><el-input-number v-model="compForm.year" :min="2000" :max="2100" /></el-form-item>
        <el-form-item label="级别">
          <el-select v-model="compForm.level"><el-option v-for="x in ['国家级','省级','校级']" :key="x" :label="x" :value="x" /></el-select>
        </el-form-item>
        <el-form-item label="类别"><el-input v-model="compForm.category" /></el-form-item>
        <el-form-item label="专业标签"><el-input v-model="compForm.major_tags" placeholder="逗号分隔" /></el-form-item>
        <el-form-item label="技术方向"><el-input v-model="compForm.tech_direction" /></el-form-item>
        <el-form-item label="状态"><el-input v-model="compForm.status" /></el-form-item>
        <el-form-item label="材料"><el-input v-model="compForm.materials" type="textarea" /></el-form-item>
        <el-form-item label="奖项设置"><el-input v-model="compForm.award_setting" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="compVisible = false">取消</el-button>
        <el-button type="primary" @click="saveComp">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="partVisible" title="新增参赛记录" width="560px">
      <el-form label-width="96px">
        <el-form-item label="竞赛">
          <el-select v-model="partForm.competition_id" style="width: 100%">
            <el-option v-for="c in comps" :key="c.id" :label="`${c.year} · ${c.name}`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="年份"><el-input-number v-model="partForm.year" :min="2000" :max="2100" /></el-form-item>
        <el-form-item label="学生"><el-input v-model="partForm.student_name" /></el-form-item>
        <el-form-item label="学号"><el-input v-model="partForm.student_id" /></el-form-item>
        <el-form-item label="专业"><el-input v-model="partForm.major" /></el-form-item>
        <el-form-item label="年级"><el-input v-model="partForm.grade" /></el-form-item>
        <el-form-item label="指导教师"><el-input v-model="partForm.instructor" /></el-form-item>
        <el-form-item label="项目"><el-input v-model="partForm.project_title" /></el-form-item>
        <el-form-item label="奖项">
          <el-select v-model="partForm.award_level">
            <el-option v-for="x in ['参赛','一等奖','二等奖','三等奖','优秀奖']" :key="x" :label="x" :value="x" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="partVisible = false">取消</el-button>
        <el-button type="primary" @click="savePart">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createCompetition,
  createParticipation,
  deleteCompetition,
  deleteParticipation,
  listCompetitions,
  listParticipations,
  updateCompetition,
} from "../api/client";

const tab = ref("comp");
const comps = ref([]);
const parts = ref([]);
const q = ref("");
const major = ref("");
const compVisible = ref(false);
const partVisible = ref(false);
const compForm = reactive(emptyComp());
const partForm = reactive(emptyPart());

function emptyComp() {
  return {
    id: null,
    name: "",
    year: new Date().getFullYear(),
    level: "校级",
    category: "学科竞赛",
    major_tags: "",
    tech_direction: "",
    status: "报名中",
    materials: "",
    award_setting: "",
    grade_range: "",
    organizer: "",
    location: "",
    fee: 0,
    description: "",
  };
}

function emptyPart() {
  return {
    competition_id: null,
    year: new Date().getFullYear(),
    student_name: "",
    student_id: "",
    major: "",
    grade: "",
    instructor: "",
    project_title: "",
    award_level: "参赛",
    team_name: "",
    award_rank: "",
    remark: "",
  };
}

async function loadComps() {
  comps.value = await listCompetitions({ q: q.value || undefined });
}

async function loadParts() {
  parts.value = await listParticipations({ major: major.value || undefined });
}

function openComp(row) {
  Object.assign(compForm, emptyComp(), row || {});
  compVisible.value = true;
}

function openPart() {
  Object.assign(partForm, emptyPart(), {
    competition_id: comps.value[0]?.id || null,
    year: comps.value[0]?.year || new Date().getFullYear(),
  });
  partVisible.value = true;
}

async function saveComp() {
  const payload = { ...compForm };
  delete payload.id;
  if (compForm.id) await updateCompetition(compForm.id, payload);
  else await createCompetition(payload);
  compVisible.value = false;
  ElMessage.success("已保存");
  await loadComps();
}

async function savePart() {
  await createParticipation({ ...partForm });
  partVisible.value = false;
  ElMessage.success("已保存");
  await loadParts();
}

async function removeComp(row) {
  await ElMessageBox.confirm(`删除竞赛「${row.name}」及其参赛记录？`, "确认", { type: "warning" });
  await deleteCompetition(row.id);
  await loadComps();
  await loadParts();
}

async function removePart(row) {
  await deleteParticipation(row.id);
  await loadParts();
}

onMounted(async () => {
  await loadComps();
  await loadParts();
});
</script>

<style scoped>
.tabs {
  padding: 0.6rem 1rem 1rem;
  min-height: calc(100vh - 120px);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
</style>
