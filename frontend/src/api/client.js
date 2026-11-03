import axios from "axios";

const http = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("ca_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function getHealth() {
  const { data } = await http.get("/health");
  return data;
}

export async function getLlmConfig() {
  const { data } = await http.get("/llm/config");
  return data;
}

export async function listProviders() {
  const { data } = await http.get("/llm/providers");
  return data;
}

export async function updateLlmConfig(payload) {
  const { data } = await http.put("/llm/config", payload);
  return data;
}

export async function testLlm() {
  const { data } = await http.post("/llm/test");
  return data;
}

export async function chatAgent(messages, context = null) {
  const payload = {
    messages,
    stream: false,
  };
  if (context) payload.context = context;
  const { data } = await http.post("/chat/agent", payload);
  return data;
}

export async function chatReviewUpload(file, question) {
  const fd = new FormData();
  fd.append("file", file);
  if (question) fd.append("question", question);
  const { data } = await http.post("/chat/agent/review-upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments() {
  const { data } = await http.get("/knowledge/documents");
  return data;
}

export async function knowledgeStats() {
  const { data } = await http.get("/knowledge/stats");
  return data;
}

export async function uploadDocument(formData) {
  const { data } = await http.post("/knowledge/documents", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function setDocumentActive(id, active) {
  const { data } = await http.patch(`/knowledge/documents/${id}`, null, {
    params: { active },
  });
  return data;
}

export async function deleteDocument(id) {
  const { data } = await http.delete(`/knowledge/documents/${id}`);
  return data;
}

export async function listCompetitions(params = {}) {
  const { data } = await http.get("/competitions", { params });
  return data;
}

export async function createCompetition(payload) {
  const { data } = await http.post("/competitions", payload);
  return data;
}

export async function updateCompetition(id, payload) {
  const { data } = await http.put(`/competitions/${id}`, payload);
  return data;
}

export async function deleteCompetition(id) {
  const { data } = await http.delete(`/competitions/${id}`);
  return data;
}

export async function listParticipations(params = {}) {
  const { data } = await http.get("/competitions/participations/list", { params });
  return data;
}

export async function createParticipation(payload) {
  const { data } = await http.post("/competitions/participations", payload);
  return data;
}

export async function deleteParticipation(id) {
  const { data } = await http.delete(`/competitions/participations/${id}`);
  return data;
}

export async function statsOverview(params = {}) {
  const { data } = await http.get("/stats/overview", { params });
  return data;
}

export async function statsCharts(params = {}) {
  const { data } = await http.get("/stats/charts", { params });
  return data;
}

export function exportUrl(kind = "participations", year) {
  const q = new URLSearchParams({ kind });
  if (year) q.set("year", String(year));
  return `/api/v1/stats/export?${q.toString()}`;
}

export async function createBudgetDraft(payload) {
  const { data } = await http.post("/workspace/budget", payload);
  return data;
}

export async function createReimbursement(payload) {
  const { data } = await http.post("/workspace/reimbursement", payload);
  return data;
}

export async function createPrepPlan(question) {
  const { data } = await http.post("/workspace/prep", { question });
  return data;
}

export async function reviewMaterial(formData) {
  const { data } = await http.post("/workspace/review", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listWorkspaceDrafts() {
  const { data } = await http.get("/workspace/drafts");
  return data;
}

export async function authRegister(payload) {
  const { data } = await http.post("/auth/register", payload);
  return data;
}

export async function authLogin(payload) {
  const { data } = await http.post("/auth/login", payload);
  return data;
}

export async function authMe() {
  const { data } = await http.get("/auth/me");
  return data;
}

export async function getTeamProfile() {
  const { data } = await http.get("/team/profile");
  return data;
}

export async function saveTeamProfile(payload) {
  const { data } = await http.put("/team/profile", payload);
  return data;
}

export async function listTeamEvents(params = {}) {
  const { data } = await http.get("/team/events", { params });
  return data;
}

export async function createTeamEvent(payload) {
  const { data } = await http.post("/team/events", payload);
  return data;
}

export async function applyTeamEvent(eventId, note = "") {
  const { data } = await http.post(`/team/events/${eventId}/apply`, { note });
  return data;
}

export async function withdrawTeamEvent(eventId) {
  const { data } = await http.post(`/team/events/${eventId}/withdraw`);
  return data;
}

export async function myTeamApplications() {
  const { data } = await http.get("/team/my-applications");
  return data;
}

export async function getTeamPool(eventId) {
  const { data } = await http.get(`/team/events/${eventId}/pool`);
  return data;
}

export async function runTeamMatch(eventId) {
  const { data } = await http.post(`/team/events/${eventId}/match`);
  return data;
}

export async function listTeams(eventId) {
  const { data } = await http.get(`/team/events/${eventId}/teams`);
  return data;
}

export async function confirmTeam(teamId, syncLedger = false) {
  const { data } = await http.post(`/team/teams/${teamId}/confirm`, {
    sync_ledger: syncLedger,
  });
  return data;
}

export async function listGuidedTeams(params = {}) {
  const { data } = await http.get("/team/my-guided-teams", { params });
  return data;
}

export async function getTeamDetail(teamId) {
  const { data } = await http.get(`/team/teams/${teamId}`);
  return data;
}

export function teamExportUrl(eventId) {
  return `/api/v1/team/events/${eventId}/export`;
}

export default http;
