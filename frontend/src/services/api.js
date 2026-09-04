import axios from "axios";

const API = axios.create({
  baseURL: "https://organic-space-engine-4pjj6wqjjvq39v-8000.app.github.dev/api" || import.meta.env.VITE_API_URL ,
});

API.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  if (user?.id) config.headers["X-User-Id"] = user.id;
  if (user?.role) config.headers["X-User-Role"] = user.role;
  return config;
});

export default API;
