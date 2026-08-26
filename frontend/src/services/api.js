import axios from "axios";

const API = axios.create({
  baseURL: "https://customer-complaint-routing.onrender.com/",
});

API.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem("user") || "null");
  if (user?.id) config.headers["X-User-Id"] = user.id;
  if (user?.role) config.headers["X-User-Role"] = user.role;
  return config;
});

export default API;
