import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://turbo-giggle-4pjj6wqjgj7cqwj5-8000.app.github.dev/",
});

API.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  if (user?.id) config.headers["X-User-Id"] = user.id;
  if (user?.role) config.headers["X-User-Role"] = user.role;
  return config;
});

export default API;
