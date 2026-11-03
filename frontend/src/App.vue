<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="mark">竞</div>
        <h1>竞赛辅助<br />服务智能体</h1>
        <p>计算与智能技术学院</p>
      </div>

      <nav class="side-nav">
        <router-link to="/">
          <el-icon><ChatDotRound /></el-icon>
          智能对话
        </router-link>
        <router-link to="/knowledge">
          <el-icon><Collection /></el-icon>
          知识库
        </router-link>
        <router-link to="/competitions">
          <el-icon><Trophy /></el-icon>
          竞赛台账
        </router-link>
        <router-link to="/analytics">
          <el-icon><DataAnalysis /></el-icon>
          数据分析
        </router-link>
        <router-link to="/workspace">
          <el-icon><Document /></el-icon>
          材料工作台
        </router-link>
        <router-link to="/team">
          <el-icon><UserFilled /></el-icon>
          智能组队
        </router-link>
        <router-link to="/settings">
          <el-icon><Setting /></el-icon>
          API 配置
        </router-link>
      </nav>

      <div class="side-foot">
        布局借鉴 ChatGPT-Web / 知识库问答开源前端<br />
        DeepSeek · LangGraph · RAG
      </div>
    </aside>

    <section class="main-area">
      <header class="topbar">
        <div>
          <h2>{{ title }}</h2>
          <p class="sub">{{ subtitle }}</p>
        </div>
        <div class="top-actions">
          <template v-if="isLoggedIn">
            <el-tag effect="plain" round>{{ displayName }} · {{ roleLabel }}</el-tag>
            <el-button size="small" @click="onLogout">退出</el-button>
          </template>
          <el-button v-else size="small" type="primary" plain @click="$router.push('/login')">登录</el-button>
          <el-tag effect="plain" type="success" round>Agent Online</el-tag>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ChatDotRound,
  Collection,
  DataAnalysis,
  Document,
  Setting,
  Trophy,
  UserFilled,
} from "@element-plus/icons-vue";
import { useAuth } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const { isLoggedIn, displayName, role, logout } = useAuth();
const title = computed(() => route.meta.title || "竞赛辅助服务智能体");
const subtitle = computed(() => route.meta.subtitle || "");
const roleLabel = computed(() => (role.value === "teacher" ? "老师" : role.value === "student" ? "学生" : ""));

function onLogout() {
  logout();
  router.push("/login");
}
</script>
