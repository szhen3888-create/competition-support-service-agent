<template>
  <section class="surface wrap">
    <div class="head">
      <div>
        <h3>LLM API 配置</h3>
        <p>默认 DeepSeek；也可切换 Qwen / 豆包 / 任意 OpenAI 兼容接口。</p>
      </div>
      <el-tag :type="healthOk ? 'success' : 'warning'" effect="dark" round>
        {{ healthOk ? "已连通" : "待配置 / 异常" }}
      </el-tag>
    </div>

    <el-form label-width="110px" class="form">
      <el-form-item label="Provider">
        <el-select v-model="form.provider" style="width: 100%" @change="onProviderChange">
          <el-option v-for="p in providers" :key="p.id" :label="p.id" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" />
      </el-form-item>
      <el-form-item label="Model">
        <el-input v-model="form.model" />
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password :placeholder="keyPlaceholder" />
      </el-form-item>
      <el-form-item label="Temperature">
        <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存并应用</el-button>
        <el-button :loading="testing" @click="runTest">测试连通</el-button>
        <el-button @click="load">刷新</el-button>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="testResult"
      :title="testResult.ok ? '测试成功' : '测试失败'"
      :type="testResult.ok ? 'success' : 'error'"
      :description="testResult.ok ? testResult.reply : testResult.error"
      show-icon
      :closable="false"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getHealth,
  getLlmConfig,
  listProviders,
  testLlm,
  updateLlmConfig,
} from "../api/client";

const providers = ref([]);
const providerDefaults = ref({});
const healthOk = ref(false);
const saving = ref(false);
const testing = ref(false);
const testResult = ref(null);
const currentMasked = ref("");
const form = reactive({
  provider: "deepseek",
  base_url: "https://api.deepseek.com",
  model: "deepseek-chat",
  api_key: "",
  temperature: 0.3,
});

const keyPlaceholder = computed(() =>
  currentMasked.value ? `已配置：${currentMasked.value}（留空不修改）` : "请输入 API Key"
);

function onProviderChange(id) {
  const d = providerDefaults.value[id];
  if (d) {
    form.base_url = d.default_base_url;
    form.model = d.default_model;
  }
}

async function load() {
  const [cfg, list, health] = await Promise.all([getLlmConfig(), listProviders(), getHealth()]);
  providers.value = list.providers || [];
  providerDefaults.value = Object.fromEntries((list.providers || []).map((p) => [p.id, p]));
  form.provider = cfg.provider;
  form.base_url = cfg.base_url;
  form.model = cfg.model;
  form.temperature = cfg.temperature;
  form.api_key = "";
  currentMasked.value = cfg.api_key_masked || "";
  healthOk.value = !!health?.llm?.ok;
}

async function save() {
  saving.value = true;
  try {
    const payload = {
      provider: form.provider,
      base_url: form.base_url,
      model: form.model,
      temperature: form.temperature,
    };
    if (form.api_key.trim()) payload.api_key = form.api_key.trim();
    const cfg = await updateLlmConfig(payload);
    currentMasked.value = cfg.api_key_masked || "";
    form.api_key = "";
    ElMessage.success("已应用");
    await load();
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function runTest() {
  testing.value = true;
  try {
    testResult.value = await testLlm();
    healthOk.value = !!testResult.value.ok;
  } catch (err) {
    testResult.value = { ok: false, error: err?.response?.data?.detail || err.message };
    healthOk.value = false;
  } finally {
    testing.value = false;
  }
}

onMounted(async () => {
  try {
    await load();
  } catch {
    ElMessage.error("加载配置失败");
  }
});
</script>

<style scoped>
.wrap {
  max-width: 720px;
  padding: 1.25rem 1.35rem 1.5rem;
}

.head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}

h3 {
  margin: 0;
  font-family: var(--font-display);
}

p {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.88rem;
}

.form {
  margin-top: 0.5rem;
}
</style>
