<template>
  <div class="page" v-if="isLoggedIn">
    <div class="toolbar">
      <div>
        <strong>{{ displayName }}</strong>
        <el-tag size="small" class="ml">{{ role === "teacher" ? "老师" : "学生" }}</el-tag>
      </div>
      <el-button @click="onLogout">退出登录</el-button>
    </div>

    <!-- 学生 -->
    <template v-if="role === 'student'">
      <section class="surface block">
        <h3>我的能力档案</h3>
        <el-form label-width="100px" class="form-grid">
          <el-form-item label="专业"><el-input v-model="profile.major" /></el-form-item>
          <el-form-item label="年级"><el-input v-model="profile.grade" placeholder="大二" /></el-form-item>
          <el-form-item label="技能标签"><el-input v-model="profile.skills" placeholder="Python,算法,Vue" /></el-form-item>
          <el-form-item label="角色意向"><el-input v-model="profile.role_prefs" placeholder="算法,开发,写材料,设计" /></el-form-item>
          <el-form-item label="水平自评">
            <el-select v-model="profile.level_self" style="width: 140px">
              <el-option label="高" value="高" />
              <el-option label="中" value="中" />
              <el-option label="初" value="初" />
            </el-select>
          </el-form-item>
          <el-form-item label="可组队时间"><el-input v-model="profile.available_time" /></el-form-item>
          <el-form-item label="意向竞赛"><el-input v-model="profile.interest_competitions" /></el-form-item>
          <el-form-item label="简介"><el-input v-model="profile.bio" type="textarea" :rows="2" /></el-form-item>
        </el-form>
        <el-button type="primary" :loading="loading" @click="saveProfile">保存档案</el-button>
      </section>

      <section class="surface block">
        <h3>可报名的组队活动</h3>
        <el-table :data="openEvents" stripe>
          <el-table-column prop="title" label="活动" min-width="160" />
          <el-table-column prop="competition_name" label="竞赛" min-width="160" />
          <el-table-column prop="team_size" label="队人数" width="90" />
          <el-table-column prop="required_roles" label="需要角色" min-width="140" />
          <el-table-column prop="applicant_count" label="已报名" width="90" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="apply(row)">报名</el-button>
              <el-button size="small" @click="withdraw(row)">撤回</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="surface block">
        <h3>我的报名</h3>
        <el-table :data="myApps" stripe>
          <el-table-column label="活动" min-width="180">
            <template #default="{ row }">{{ row.event?.title }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
        </el-table>
      </section>
    </template>

    <!-- 老师 -->
    <template v-else>
      <section class="surface block">
        <h3>创建组队活动</h3>
        <el-form label-width="100px">
          <el-form-item label="活动标题"><el-input v-model="eventForm.title" /></el-form-item>
          <el-form-item label="关联竞赛">
            <el-select v-model="eventForm.competition_id" clearable filterable placeholder="可选台账竞赛" style="width: 100%" @change="onCompPick">
              <el-option v-for="c in competitions" :key="c.id" :label="`${c.name}（${c.year}）`" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="竞赛名称"><el-input v-model="eventForm.competition_name" placeholder="未选台账时手填" /></el-form-item>
          <el-form-item label="每队人数"><el-input-number v-model="eventForm.team_size" :min="2" :max="10" /></el-form-item>
          <el-form-item label="需要角色"><el-input v-model="eventForm.required_roles" placeholder="算法,开发,写材料" /></el-form-item>
          <el-form-item label="说明"><el-input v-model="eventForm.description" type="textarea" :rows="2" /></el-form-item>
          <el-button type="primary" :loading="loading" @click="createEvent">创建活动</el-button>
        </el-form>
      </section>

      <section class="surface block">
        <h3>我的活动</h3>
        <el-table :data="myEvents" stripe highlight-current-row @current-change="selectEvent">
          <el-table-column prop="title" label="活动" min-width="160" />
          <el-table-column prop="competition_name" label="竞赛" min-width="160" />
          <el-table-column prop="applicant_count" label="报名人数" width="100" />
          <el-table-column prop="status" label="状态" width="90" />
        </el-table>
        <p class="tip-line">点击一行活动，可查看报名池并执行 AI 组队。</p>
      </section>

      <section class="surface block">
        <div class="row-head">
          <h3>指导队伍</h3>
          <div class="sum-tags">
            <el-tag size="small">共 {{ guidedSummary.total || 0 }} 支</el-tag>
            <el-tag size="small" type="success">已确认 {{ guidedSummary.confirmed || 0 }}</el-tag>
            <el-tag size="small" type="info">草案 {{ guidedSummary.draft || 0 }}</el-tag>
            <el-select v-model="guidedFilter" size="small" style="width: 120px" @change="loadGuidedTeams">
              <el-option label="全部状态" value="" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="草案" value="draft" />
            </el-select>
            <el-button size="small" @click="loadGuidedTeams">刷新</el-button>
          </div>
        </div>
        <el-table :data="guidedTeams" stripe empty-text="暂无队伍：请先创建活动、学生报名后执行 AI 组队并确认">
          <el-table-column prop="name" label="队伍" width="110" />
          <el-table-column prop="event_title" label="所属活动" min-width="140" />
          <el-table-column prop="competition_name" label="竞赛" min-width="140" />
          <el-table-column prop="member_count" label="人数" width="70" />
          <el-table-column prop="roles_summary" label="队员与角色" min-width="200" show-overflow-tooltip />
          <el-table-column prop="score" label="匹配分" width="80" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'confirmed' ? 'success' : 'info'">
                {{ row.status === "confirmed" ? "已确认" : "草案" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openTeamDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <el-drawer v-model="detailVisible" title="队伍信息" size="420px" destroy-on-close>
        <template v-if="teamDetail">
          <div class="detail-block">
            <p><b>队名：</b>{{ teamDetail.name }}</p>
            <p><b>状态：</b>{{ teamDetail.status === "confirmed" ? "已确认" : "草案" }}</p>
            <p><b>所属活动：</b>{{ teamDetail.event_title || teamDetail.event?.title }}</p>
            <p><b>竞赛：</b>{{ teamDetail.competition_name }}</p>
            <p><b>指导教师：</b>{{ teamDetail.instructor || displayName }}</p>
            <p><b>匹配得分：</b>{{ teamDetail.score }}</p>
            <p><b>组队说明：</b>{{ teamDetail.reason || "—" }}</p>
          </div>
          <h4>队员信息</h4>
          <el-table :data="teamDetail.members || []" size="small" stripe>
            <el-table-column prop="name" label="姓名" width="80" />
            <el-table-column prop="suggested_role" label="角色" width="80" />
            <el-table-column label="队长" width="60">
              <template #default="{ row }">{{ row.is_leader ? "是" : "" }}</template>
            </el-table-column>
            <el-table-column prop="major" label="专业" min-width="90" />
            <el-table-column prop="grade" label="年级" width="60" />
            <el-table-column prop="level_self" label="水平" width="55" />
            <el-table-column prop="skills" label="技能" min-width="100" show-overflow-tooltip />
          </el-table>
          <div v-if="(teamDetail.members || []).some((m) => m.bio)" class="bio-list">
            <h4>队员简介</h4>
            <p v-for="m in teamDetail.members.filter((x) => x.bio)" :key="m.user_id">
              <b>{{ m.name }}：</b>{{ m.bio }}
            </p>
          </div>
          <div class="drawer-actions">
            <el-button
              v-if="teamDetail.status !== 'confirmed'"
              type="success"
              :loading="loading"
              @click="doConfirm(teamDetail)"
            >
              确认成队
            </el-button>
            <el-checkbox v-if="teamDetail.status !== 'confirmed'" v-model="syncMap[teamDetail.id]">
              同步到竞赛台账
            </el-checkbox>
          </div>
        </template>
      </el-drawer>

      <section class="surface block" v-if="currentEvent">
        <div class="row-head">
          <h3>报名池 · {{ currentEvent.title }}</h3>
          <div>
            <el-button :loading="matching" type="primary" @click="doMatch">AI 辅助组队</el-button>
            <el-button :loading="loading" @click="doExport">导出 Excel</el-button>
          </div>
        </div>
        <el-table :data="pool" stripe size="small">
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="major" label="专业" width="120" />
          <el-table-column prop="grade" label="年级" width="80" />
          <el-table-column label="技能">
            <template #default="{ row }">{{ (row.skills || []).join("、") }}</template>
          </el-table-column>
          <el-table-column label="角色意向">
            <template #default="{ row }">{{ (row.role_prefs || []).join("、") }}</template>
          </el-table-column>
          <el-table-column prop="level" label="水平" width="70" />
        </el-table>

        <div v-if="aiExplain" class="ai-box">
          <h4>AI 解释与微调建议</h4>
          <pre>{{ aiExplain }}</pre>
        </div>

        <div class="teams">
          <div v-for="t in teams" :key="t.id" class="team-card surface">
            <div class="team-head">
              <strong>{{ t.name }}</strong>
              <el-tag size="small">{{ t.status }}</el-tag>
              <span class="score">得分 {{ t.score }}</span>
            </div>
            <p class="reason">{{ t.reason }}</p>
            <ul>
              <li v-for="m in t.members" :key="m.user_id">
                {{ m.name }} · {{ m.suggested_role }}
                <el-tag v-if="m.is_leader" size="small" type="warning">队长</el-tag>
              </li>
            </ul>
            <el-checkbox v-model="syncMap[t.id]">确认时同步到竞赛台账</el-checkbox>
            <el-button
              size="small"
              type="success"
              :disabled="t.status === 'confirmed'"
              :loading="loading"
              @click="doConfirm(t)"
            >
              确认成队
            </el-button>
          </div>
        </div>
        <div v-if="leftovers.length" class="left">
          <h4>暂未入队</h4>
          <p>{{ leftovers.map((x) => x.name).join("、") }}</p>
        </div>
      </section>
    </template>
  </div>
  <div v-else class="page">
    <el-empty description="请先登录">
      <el-button type="primary" @click="$router.push('/login')">去登录</el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  applyTeamEvent,
  confirmTeam,
  createTeamEvent,
  getTeamDetail,
  getTeamPool,
  getTeamProfile,
  listCompetitions,
  listGuidedTeams,
  listTeamEvents,
  listTeams,
  myTeamApplications,
  runTeamMatch,
  saveTeamProfile,
  withdrawTeamEvent,
} from "../api/client";
import http from "../api/client";
import { useAuth } from "../stores/auth";

const router = useRouter();
const { isLoggedIn, role, displayName, logout } = useAuth();
const loading = ref(false);
const matching = ref(false);
const guidedTeams = ref([]);
const guidedSummary = ref({ total: 0, confirmed: 0, draft: 0 });
const guidedFilter = ref("");
const detailVisible = ref(false);
const teamDetail = ref(null);
const profile = reactive({
  major: "",
  grade: "",
  skills: "",
  role_prefs: "",
  level_self: "中",
  available_time: "",
  interest_competitions: "",
  bio: "",
});
const openEvents = ref([]);
const myApps = ref([]);
const myEvents = ref([]);
const competitions = ref([]);
const currentEvent = ref(null);
const pool = ref([]);
const teams = ref([]);
const leftovers = ref([]);
const aiExplain = ref("");
const syncMap = reactive({});
const eventForm = reactive({
  title: "",
  competition_id: null,
  competition_name: "",
  team_size: 3,
  required_roles: "算法,开发,写材料",
  description: "",
});

function onLogout() {
  logout();
  router.push("/login");
}

async function loadStudent() {
  const p = await getTeamProfile();
  Object.assign(profile, p.profile || {});
  const ev = await listTeamEvents({ status: "open" });
  // 学生 list_events 不过滤老师，后端对老师过滤；学生看全部 open —— 需后端对学生返回全部 open
  openEvents.value = (ev.items || []).filter((x) => x.status === "open");
  const apps = await myTeamApplications();
  myApps.value = apps.items || [];
}

async function loadGuidedTeams() {
  const res = await listGuidedTeams(guidedFilter.value ? { status: guidedFilter.value } : {});
  guidedTeams.value = res.items || [];
  guidedSummary.value = res.summary || { total: 0, confirmed: 0, draft: 0 };
}

async function openTeamDetail(row) {
  try {
    teamDetail.value = await getTeamDetail(row.id);
    detailVisible.value = true;
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  }
}

async function loadTeacher() {
  const ev = await listTeamEvents();
  myEvents.value = ev.items || [];
  const comps = await listCompetitions({});
  competitions.value = Array.isArray(comps) ? comps : comps.items || [];
  await loadGuidedTeams();
}

async function doExport() {
  if (!currentEvent.value) return;
  loading.value = true;
  try {
    const res = await http.get(`/team/events/${currentEvent.value.id}/export`, {
      responseType: "blob",
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `team_event_${currentEvent.value.id}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

function onCompPick(id) {
  const c = competitions.value.find((x) => x.id === id);
  if (c) {
    eventForm.competition_name = c.name;
    if (!eventForm.title) eventForm.title = `${c.name}组队`;
  }
}

async function saveProfile() {
  loading.value = true;
  try {
    await saveTeamProfile({ ...profile });
    ElMessage.success("档案已保存");
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

async function apply(row) {
  try {
    await applyTeamEvent(row.id);
    ElMessage.success("报名成功");
    await loadStudent();
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  }
}

async function withdraw(row) {
  try {
    await withdrawTeamEvent(row.id);
    ElMessage.success("已撤回");
    await loadStudent();
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  }
}

async function createEvent() {
  loading.value = true;
  try {
    await createTeamEvent({ ...eventForm });
    ElMessage.success("活动已创建");
    eventForm.title = "";
    eventForm.description = "";
    await loadTeacher();
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

async function selectEvent(row) {
  if (!row) return;
  currentEvent.value = row;
  aiExplain.value = "";
  leftovers.value = [];
  const p = await getTeamPool(row.id);
  pool.value = p.items || [];
  const t = await listTeams(row.id);
  teams.value = t.items || [];
}

async function doMatch() {
  if (!currentEvent.value) return;
  matching.value = true;
  try {
    const res = await runTeamMatch(currentEvent.value.id);
    teams.value = res.teams || [];
    leftovers.value = res.leftovers || [];
    aiExplain.value = res.ai_explain || "";
    const p = await getTeamPool(currentEvent.value.id);
    pool.value = p.items || [];
    ElMessage.success("已生成组队草案");
    await loadGuidedTeams();
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  } finally {
    matching.value = false;
  }
}

async function doConfirm(t) {
  loading.value = true;
  try {
    const res = await confirmTeam(t.id, !!syncMap[t.id]);
    ElMessage.success(res.synced_participations ? `已确认，并同步 ${res.synced_participations} 条台账` : "已确认成队");
    if (currentEvent.value) {
      const list = await listTeams(currentEvent.value.id);
      teams.value = list.items || [];
    }
    await loadGuidedTeams();
    if (detailVisible.value && teamDetail.value?.id === t.id) {
      teamDetail.value = await getTeamDetail(t.id);
    }
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!isLoggedIn.value) return;
  try {
    if (role.value === "student") await loadStudent();
    else await loadTeacher();
  } catch (e) {
    ElMessage.error(String(e?.response?.data?.detail || e.message));
  }
});
</script>

<style scoped>
.page {
  display: grid;
  gap: 1rem;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ml {
  margin-left: 0.5rem;
}
.block {
  padding: 1rem 1.1rem 1.15rem;
}
.block h3 {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
}
.row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
.row-head h3 {
  margin: 0;
}
.teams {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.85rem;
  margin-top: 1rem;
}
.team-card {
  padding: 0.85rem 1rem;
}
.team-head {
  display: flex;
  gap: 0.45rem;
  align-items: center;
}
.score {
  margin-left: auto;
  color: var(--muted);
  font-size: 0.85rem;
}
.reason {
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.45;
}
.ai-box {
  margin-top: 1rem;
  padding: 0.75rem 0.9rem;
  background: #f7faf9;
  border-radius: 12px;
  border: 1px solid var(--line);
}
.ai-box pre {
  white-space: pre-wrap;
  margin: 0.4rem 0 0;
  font-family: inherit;
  line-height: 1.55;
  font-size: 0.9rem;
}
.left {
  margin-top: 0.85rem;
  color: var(--muted);
}
.tip-line {
  margin: 0.65rem 0 0;
  color: var(--muted);
  font-size: 0.82rem;
}
.sum-tags {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}
.detail-block p {
  margin: 0.35rem 0;
  line-height: 1.5;
  font-size: 0.92rem;
}
.bio-list {
  margin-top: 0.85rem;
}
.bio-list p {
  margin: 0.3rem 0;
  color: var(--muted);
  font-size: 0.86rem;
}
.drawer-actions {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
