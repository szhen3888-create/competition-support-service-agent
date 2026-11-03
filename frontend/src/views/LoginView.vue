<template>
  <div class="login-wrap">
    <div class="surface card">
      <h2>{{ mode === "login" ? "登录" : "注册" }}</h2>
      <p class="hint">智能组队需要账号。演示：老师 teacher1 / teacher123；学生 stu1 / stu123</p>
      <el-form label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="显示名">
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="角色">
          <el-radio-group v-model="form.role">
            <el-radio-button value="student">学生</el-radio-button>
            <el-radio-button value="teacher">老师</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
          {{ mode === "login" ? "登录" : "注册并登录" }}
        </el-button>
      </el-form>
      <button class="switch" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === "login" ? "没有账号？去注册" : "已有账号？去登录" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { authLogin, authRegister } from "../api/client";
import { useAuth } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const { setSession } = useAuth();
const mode = ref("login");
const loading = ref(false);
const form = reactive({
  username: "",
  password: "",
  display_name: "",
  role: "student",
});

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning("请填写用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const res =
      mode.value === "login"
        ? await authLogin({ username: form.username, password: form.password })
        : await authRegister({
            username: form.username,
            password: form.password,
            role: form.role,
            display_name: form.display_name || form.username,
          });
    setSession(res.token, res.user);
    ElMessage.success("登录成功");
    router.replace(route.query.redirect || "/team");
  } catch (err) {
    ElMessage.error(String(err?.response?.data?.detail || err.message));
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: calc(100vh - 120px);
  display: grid;
  place-items: center;
  padding: 1rem;
}
.card {
  width: min(420px, 100%);
  padding: 1.4rem 1.5rem 1.2rem;
}
h2 {
  margin: 0 0 0.35rem;
  font-family: var(--font-display);
}
.hint {
  color: var(--muted);
  font-size: 0.85rem;
  line-height: 1.45;
  margin: 0 0 1rem;
}
.switch {
  margin-top: 0.9rem;
  border: 0;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  width: 100%;
}
</style>
