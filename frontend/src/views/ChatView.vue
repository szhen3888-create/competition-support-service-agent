<template>
  <div class="chat-layout">
    <aside class="history surface">
      <div class="hist-head">
        <strong>会话</strong>
        <el-button size="small" type="primary" plain @click="newChat">新建</el-button>
      </div>
      <div
        v-for="s in sessions"
        :key="s.id"
        class="hist-item"
        :class="{ active: s.id === activeId }"
        @click="activeId = s.id"
      >
        <div class="hist-title">{{ s.title }}</div>
        <div class="hist-meta">{{ s.messages.length }} 条消息</div>
      </div>
      <div class="hints">
        <p>能力快捷入口</p>
        <button v-for="q in samples" :key="q" @click="ask(q)">{{ q }}</button>
      </div>
    </aside>

    <section class="chat-main surface">
      <div class="messages" ref="listRef">
        <div v-if="!current.messages.length" class="hero">
          <h3>你好，我是竞赛助手</h3>
          <p>
            可直接对话完成：知识问答、备赛计划、材料初审、预算/借款/报销、统计出图。
            知识库作依据，不会因缺原文就空白拒答。
          </p>
        </div>

        <div
          v-for="(m, idx) in current.messages"
          :key="idx"
          class="row"
          :class="m.role"
        >
          <div class="avatar">{{ m.role === "user" ? "我" : "AI" }}</div>
          <div class="bubble">
            <div class="meta" v-if="m.intent">
              <span class="pill">{{ m.intent }}</span>
            </div>
            <div
              v-if="m.role === 'assistant'"
              class="md"
              v-html="renderMarkdown(m.content)"
            />
            <div v-else class="plain">{{ m.content }}</div>

            <div v-if="m.artifacts?.length" class="arts">
              <template v-for="(a, ai) in m.artifacts" :key="ai">
                <a
                  v-if="a.type === 'file' && a.url"
                  class="art-file"
                  :href="a.url"
                  target="_blank"
                  rel="noopener"
                >
                  下载 {{ a.title || a.filename || "文件" }}
                </a>
                <div v-else-if="a.type === 'chart'" class="art-chart">
                  <div class="art-chart-title">{{ a.title || "统计图" }}</div>
                  <div
                    class="chart-el"
                    :ref="(el) => bindChart(el, a.option, `${idx}-${ai}`)"
                  />
                </div>
              </template>
            </div>

            <div v-if="m.citations?.length" class="cites">
              <div v-for="c in m.citations" :key="c.index" class="cite">
                <b>[{{ c.index }}]</b>
                <span>{{ c.title || c.filename }}</span>
                <em v-if="c.page">p.{{ c.page }}</em>
              </div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="row assistant">
          <div class="avatar">AI</div>
          <div class="bubble typing">正在调用工具并生成…</div>
        </div>
      </div>

      <form class="composer" @submit.prevent="onSend">
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入问题，Enter 发送 / Shift+Enter 换行；可上传材料做初审"
          @keydown.enter.exact.prevent="onSend"
        />
        <div class="composer-actions">
          <div class="left-actions">
            <input
              ref="fileRef"
              type="file"
              accept=".pdf,.doc,.docx,.txt,.md"
              class="hidden-file"
              @change="onFile"
            />
            <el-button @click="fileRef?.click()" :disabled="loading">上传材料初审</el-button>
            <span class="tip">支持 PDF / Word / 文本</span>
          </div>
          <div>
            <el-button @click="clearCurrent" :disabled="loading">清空本会话</el-button>
            <el-button type="primary" native-type="submit" :loading="loading">发送</el-button>
          </div>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { chatAgent, chatReviewUpload } from "../api/client";
import { renderMarkdown } from "../utils/markdown";

const samples = [
  "大挑报名要注意什么？",
  "给软件工程大二做个蓝桥备赛计划",
  "3人去外省参赛，报名费300，交通400，住2晚每晚200，做预算",
  "2026年各专业获奖人数，出图",
  "推荐适合软件工程大二的竞赛",
];

const sessions = reactive([{ id: 1, title: "新的对话", messages: [] }]);
const activeId = ref(1);
const input = ref("");
const loading = ref(false);
const listRef = ref(null);
const fileRef = ref(null);
const chartMap = new Map();

const current = computed(() => sessions.find((s) => s.id === activeId.value) || sessions[0]);

async function scrollBottom() {
  await nextTick();
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight;
}

function newChat() {
  const id = Date.now();
  sessions.unshift({ id, title: "新的对话", messages: [] });
  activeId.value = id;
}

function clearCurrent() {
  current.value.messages = [];
  current.value.title = "新的对话";
  disposeCharts();
}

function ask(q) {
  input.value = q;
  onSend();
}

function disposeCharts() {
  for (const c of chartMap.values()) c.dispose();
  chartMap.clear();
}

function bindChart(el, option, key) {
  if (!el || !option) return;
  nextTick(() => {
    let chart = chartMap.get(key);
    if (!chart) {
      chart = echarts.init(el);
      chartMap.set(key, chart);
    }
    chart.setOption(option, true);
    chart.resize();
  });
}

onBeforeUnmount(() => disposeCharts());

async function onSend() {
  const text = input.value.trim();
  if (!text || loading.value) return;
  const sess = current.value;
  sess.messages.push({ role: "user", content: text });
  if (sess.title === "新的对话") sess.title = text.slice(0, 18);
  input.value = "";
  loading.value = true;
  await scrollBottom();
  try {
    const payload = sess.messages.map((m) => ({ role: m.role, content: m.content }));
    const res = await chatAgent(payload);
    sess.messages.push({
      role: "assistant",
      content: res.content || "(空响应)",
      intent: res.intent,
      citations: res.citations || [],
      artifacts: res.artifacts || [],
    });
  } catch (err) {
    ElMessage.error(String(err?.response?.data?.detail || err.message));
  } finally {
    loading.value = false;
    await scrollBottom();
  }
}

async function onFile(ev) {
  const file = ev.target.files?.[0];
  ev.target.value = "";
  if (!file || loading.value) return;
  const sess = current.value;
  const q = input.value.trim() || "请对上传材料做初审，给出修改建议和 5 道答辩题";
  sess.messages.push({ role: "user", content: `【上传材料】${file.name}\n${q}` });
  if (sess.title === "新的对话") sess.title = `初审 ${file.name}`.slice(0, 18);
  input.value = "";
  loading.value = true;
  await scrollBottom();
  try {
    const res = await chatReviewUpload(file, q);
    sess.messages.push({
      role: "assistant",
      content: res.content || "(空响应)",
      intent: res.intent || "review_assist",
      citations: res.citations || [],
      artifacts: res.artifacts || [],
    });
  } catch (err) {
    ElMessage.error(String(err?.response?.data?.detail || err.message));
  } finally {
    loading.value = false;
    await scrollBottom();
  }
}
</script>

<style scoped>
.chat-layout {
  height: calc(100vh - 110px);
  min-height: 560px;
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 1rem;
}

.history,
.chat-main {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hist-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.95rem 1rem;
  border-bottom: 1px solid var(--line);
}

.hist-item {
  margin: 0.45rem 0.65rem;
  padding: 0.75rem 0.8rem;
  border-radius: 12px;
  cursor: pointer;
  border: 1px solid transparent;
}

.hist-item:hover,
.hist-item.active {
  background: var(--accent-soft);
  border-color: rgba(15, 118, 110, 0.2);
}

.hist-title {
  font-weight: 600;
  font-size: 0.92rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hist-meta {
  margin-top: 0.2rem;
  color: var(--muted);
  font-size: 0.75rem;
}

.hints {
  margin-top: auto;
  padding: 0.9rem;
  border-top: 1px solid var(--line);
  max-height: 42%;
  overflow: auto;
}

.hints p {
  margin: 0 0 0.45rem;
  color: var(--muted);
  font-size: 0.78rem;
}

.hints button {
  display: block;
  width: 100%;
  text-align: left;
  margin-bottom: 0.4rem;
  border: 1px dashed var(--line);
  background: #f8fbfa;
  border-radius: 10px;
  padding: 0.55rem 0.65rem;
  color: var(--ink);
  cursor: pointer;
  font-size: 0.8rem;
  line-height: 1.35;
}

.messages {
  flex: 1;
  overflow: auto;
  padding: 1.2rem 1.3rem;
}

.hero {
  max-width: 560px;
  margin: 10vh auto 0;
  text-align: center;
}

.hero h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.7rem;
}

.hero p {
  color: var(--muted);
  line-height: 1.6;
}

.row {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1.1rem;
}

.row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  flex: none;
  background: var(--accent-soft);
  color: var(--accent);
}

.row.user .avatar {
  background: #f7e7d8;
  color: var(--accent-2);
}

.bubble {
  max-width: min(760px, 90%);
  padding: 0.85rem 1rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: #fbfcfc;
}

.row.user .bubble {
  background: #fff7ef;
  border-color: rgba(196, 107, 45, 0.18);
}

.plain {
  white-space: pre-wrap;
  line-height: 1.6;
}

.md :deep(p) {
  margin: 0 0 0.55rem;
  line-height: 1.65;
}

.md :deep(ul),
.md :deep(ol) {
  margin: 0.2rem 0 0.6rem;
  padding-left: 1.2rem;
}

.md :deep(pre) {
  border-radius: 10px;
  overflow: auto;
  padding: 0.75rem;
}

.meta {
  margin-bottom: 0.4rem;
}

.pill {
  display: inline-block;
  font-size: 0.72rem;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: var(--accent);
}

.arts {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.55rem;
}

.art-file {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 0.45rem 0.75rem;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--accent);
  text-decoration: none;
  font-size: 0.86rem;
  font-weight: 600;
}

.art-chart {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.55rem 0.65rem 0.75rem;
  background: #fff;
}

.art-chart-title {
  font-size: 0.82rem;
  color: var(--muted);
  margin-bottom: 0.35rem;
}

.chart-el {
  width: 100%;
  height: 260px;
}

.cites {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.35rem;
}

.cite {
  font-size: 0.78rem;
  color: var(--muted);
  background: #f3f7f6;
  border-radius: 8px;
  padding: 0.4rem 0.55rem;
  display: flex;
  gap: 0.4rem;
  align-items: baseline;
}

.cite em {
  font-style: normal;
  opacity: 0.7;
}

.typing {
  color: var(--muted);
}

.composer {
  border-top: 1px solid var(--line);
  padding: 0.9rem 1rem 1rem;
  background: linear-gradient(180deg, #fff, #f7faf9);
}

.composer-actions {
  margin-top: 0.65rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.left-actions {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.hidden-file {
  display: none;
}

.tip {
  color: var(--muted);
  font-size: 0.78rem;
}

@media (max-width: 980px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }
  .history {
    display: none;
  }
}
</style>
