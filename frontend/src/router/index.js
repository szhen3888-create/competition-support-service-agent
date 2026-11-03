import { createRouter, createWebHistory } from "vue-router";
import ChatView from "../views/ChatView.vue";
import KnowledgeView from "../views/KnowledgeView.vue";
import CompetitionsView from "../views/CompetitionsView.vue";
import AnalyticsView from "../views/AnalyticsView.vue";
import WorkspaceView from "../views/WorkspaceView.vue";
import SettingsView from "../views/SettingsView.vue";
import LoginView from "../views/LoginView.vue";
import TeamView from "../views/TeamView.vue";
import { useAuth } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: {
        title: "登录",
        subtitle: "老师 / 学生账号",
        public: true,
      },
    },
    {
      path: "/",
      name: "chat",
      component: ChatView,
      meta: {
        title: "智能对话",
        subtitle: "政策问答走知识库引用；统计类问题请配合台账数据",
      },
    },
    {
      path: "/knowledge",
      name: "knowledge",
      component: KnowledgeView,
      meta: {
        title: "知识库",
        subtitle: "上传通知 / 规程 / 政策，支持原文引用",
      },
    },
    {
      path: "/competitions",
      name: "competitions",
      component: CompetitionsView,
      meta: {
        title: "竞赛台账",
        subtitle: "结构化维护竞赛与参赛获奖记录",
      },
    },
    {
      path: "/analytics",
      name: "analytics",
      component: AnalyticsView,
      meta: {
        title: "数据分析",
        subtitle: "基于台账的统计图表与 Excel 导出",
      },
    },
    {
      path: "/workspace",
      name: "workspace",
      component: WorkspaceView,
      meta: {
        title: "材料工作台",
        subtitle: "备赛计划 / 材料初审 / 预算借款报销草稿与导出",
      },
    },
    {
      path: "/team",
      name: "team",
      component: TeamView,
      meta: {
        title: "智能组队",
        subtitle: "师生提交信息，按竞赛活动 AI 辅助组队",
        requiresAuth: true,
      },
    },
    {
      path: "/settings",
      name: "settings",
      component: SettingsView,
      meta: {
        title: "API 配置",
        subtitle: "默认 DeepSeek，可切换 OpenAI 兼容接口",
      },
    },
  ],
});

router.beforeEach((to) => {
  const { isLoggedIn } = useAuth();
  if (to.meta.requiresAuth && !isLoggedIn.value) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  return true;
});

export default router;
