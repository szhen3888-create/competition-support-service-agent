<template>
  <div class="page">
    <div class="toolbar">
      <el-select v-model="year" clearable placeholder="全部年份" style="width: 140px" @change="reload">
        <el-option v-for="y in years" :key="y" :label="String(y)" :value="y" />
      </el-select>
      <div class="export">
        <el-button @click="download('competitions')">导出竞赛表</el-button>
        <el-button type="primary" @click="download('participations')">导出参赛表</el-button>
      </div>
    </div>

    <div class="kpi">
      <div class="surface card" v-for="k in kpiCards" :key="k.label">
        <span>{{ k.label }}</span>
        <strong>{{ k.value }}</strong>
      </div>
    </div>

    <div class="charts">
      <div class="surface chart-box">
        <h4>奖项分布</h4>
        <div ref="awardRef" class="chart" />
      </div>
      <div class="surface chart-box">
        <h4>专业参赛量</h4>
        <div ref="majorRef" class="chart" />
      </div>
      <div class="surface chart-box">
        <h4>年度趋势</h4>
        <div ref="yearRef" class="chart" />
      </div>
      <div class="surface chart-box">
        <h4>指导教师指导量 Top10</h4>
        <div ref="instRef" class="chart" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { exportUrl, statsCharts, statsOverview } from "../api/client";

const year = ref();
const years = [2026, 2025, 2024, 2023];
const overview = ref({});
const charts = ref({});
const awardRef = ref(null);
const majorRef = ref(null);
const yearRef = ref(null);
const instRef = ref(null);
const instances = [];

const kpiCards = computed(() => [
  { label: "竞赛数", value: overview.value.competition_count || 0 },
  { label: "参赛人次", value: overview.value.participation_count || 0 },
  { label: "获奖人次", value: overview.value.award_count || 0 },
  { label: "指导教师", value: overview.value.instructor_count || 0 },
]);

function mount(el, option) {
  if (!el) return;
  const chart = echarts.init(el);
  chart.setOption(option);
  instances.push(chart);
}

function paint() {
  instances.splice(0).forEach((c) => c.dispose());
  const c = charts.value || {};
  mount(awardRef.value, {
    color: ["#0f766e", "#c46b2d", "#1b3554", "#59a5a0", "#d9a066"],
    tooltip: { trigger: "item" },
    series: [{ type: "pie", radius: ["42%", "68%"], data: c.award_pie || [] }],
  });
  mount(majorRef.value, {
    color: ["#0f766e"],
    grid: { left: 40, right: 16, top: 24, bottom: 32 },
    xAxis: { type: "category", data: c.major_bar?.categories || [], axisLabel: { rotate: 20 } },
    yAxis: { type: "value", minInterval: 1 },
    series: [{ type: "bar", data: c.major_bar?.values || [], barWidth: 28, itemStyle: { borderRadius: [8, 8, 0, 0] } }],
  });
  mount(yearRef.value, {
    color: ["#c46b2d"],
    grid: { left: 40, right: 16, top: 24, bottom: 28 },
    xAxis: { type: "category", data: c.year_line?.categories || [] },
    yAxis: { type: "value", minInterval: 1 },
    series: [{ type: "line", smooth: true, areaStyle: { opacity: 0.12 }, data: c.year_line?.values || [] }],
  });
  mount(instRef.value, {
    color: ["#1b3554"],
    grid: { left: 72, right: 16, top: 16, bottom: 28 },
    xAxis: { type: "value", minInterval: 1 },
    yAxis: { type: "category", data: (c.instructor_bar?.categories || []).slice().reverse() },
    series: [{ type: "bar", data: (c.instructor_bar?.values || []).slice().reverse(), barWidth: 16, itemStyle: { borderRadius: [0, 8, 8, 0] } }],
  });
}

async function reload() {
  const params = year.value ? { year: year.value } : {};
  overview.value = await statsOverview(params);
  charts.value = await statsCharts(params);
  await nextTick();
  paint();
}

function download(kind) {
  window.open(exportUrl(kind, year.value), "_blank");
  ElMessage.success("开始下载");
}

function onResize() {
  instances.forEach((c) => c.resize());
}

onMounted(async () => {
  await reload();
  window.addEventListener("resize", onResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", onResize);
  instances.splice(0).forEach((c) => c.dispose());
});
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.kpi {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.card {
  padding: 1rem 1.1rem;
}

.card span {
  color: var(--muted);
  font-size: 0.82rem;
}

.card strong {
  display: block;
  margin-top: 0.35rem;
  font-family: var(--font-display);
  font-size: 1.7rem;
  color: var(--ink);
}

.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.chart-box {
  padding: 0.9rem 1rem 0.4rem;
}

.chart-box h4 {
  margin: 0 0 0.35rem;
  font-family: var(--font-display);
  font-size: 0.98rem;
}

.chart {
  height: 280px;
}

@media (max-width: 980px) {
  .kpi,
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
