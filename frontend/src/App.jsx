import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import CustomerDashboard from "./pages/CustomerDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import AgentDashboard from "./pages/AgentDashboard";

function Guard({ roles, children }) {
  let user = null;

  try {
    user = JSON.parse(
      localStorage.getItem("user") || "null"
    );
  } catch {
    localStorage.removeItem("user");
  }

  if (
    !user ||
    !roles.includes(user.role)
  ) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return children;
}

export default function App() {
  return <Routes>
    <Route path="/" element={<Login />} />
    <Route path="/customer" element={<Guard roles={["customer"]}><CustomerDashboard /></Guard>} />
    <Route path="/admin" element={<Guard roles={["admin"]}><AdminDashboard /></Guard>} />
    <Route path="/agent" element={<Guard roles={["agent"]}><AgentDashboard /></Guard>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
