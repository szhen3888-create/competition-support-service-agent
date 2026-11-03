import { computed, reactive } from "vue";

const state = reactive({
  token: localStorage.getItem("ca_token") || "",
  user: JSON.parse(localStorage.getItem("ca_user") || "null"),
});

export function useAuth() {
  const isLoggedIn = computed(() => !!state.token);
  const role = computed(() => state.user?.role || "");
  const displayName = computed(() => state.user?.display_name || state.user?.username || "");

  function setSession(token, user) {
    state.token = token || "";
    state.user = user || null;
    if (token) localStorage.setItem("ca_token", token);
    else localStorage.removeItem("ca_token");
    if (user) localStorage.setItem("ca_user", JSON.stringify(user));
    else localStorage.removeItem("ca_user");
  }

  function logout() {
    setSession("", null);
  }

  return { state, isLoggedIn, role, displayName, setSession, logout };
}
