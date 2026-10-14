import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "https://crispy-memory-qrjx75pq46c49x5-8000.app.github.dev/api",
});

API.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  if (user?.id) config.headers["X-User-Id"] = user.id;
  if (user?.role) config.headers["X-User-Role"] = user.role;
  return config;
});

export default API;
