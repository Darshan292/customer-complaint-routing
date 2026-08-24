import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiShield, FiUser, FiHeadphones, FiLock } from "react-icons/fi";
import API from "../services/api";
import "./Login.css";

export default function Login() {
  const [email,setEmail]=useState(""); const [password,setPassword]=useState(""); const [error,setError]=useState("");
  const navigate=useNavigate();
  const submit = async (e) => {
    e.preventDefault();

    setError("");

    try {
      const response = await API.post(
        "/login",
        {
          email,
          password,
        }
      );

      const data = response.data;

      const normalizedUser = {
        ...data,
        role:
          data.role === "user"
            ? "customer"
            : data.role,
      };

      localStorage.setItem(
        "user",
        JSON.stringify(
          normalizedUser
        )
      );

      if (
        normalizedUser.role === "admin"
      ) {
        navigate("/admin");
        return;
      }

      if (
        normalizedUser.role === "agent"
      ) {
        navigate("/agent");
        return;
      }

      if (
        normalizedUser.role === "customer"
      ) {
        navigate("/customer");
        return;
      }

      setError(
        "Unsupported account role."
      );

    } catch (err) {

      setError(
        err.response?.data?.detail ||
        "Unable to connect to the operations platform"
      );
    }
  };
  return <main className="enterprise-login"><section className="login-shell"><div className="brand"><div className="brand-mark"><FiShield /></div><div><b>Support Operations</b><span>Enterprise Complaint Platform</span></div></div><div className="login-copy"><span className="eyebrow">OPERATIONS CONTROL PLANE</span><h1>Resolve every customer issue with the right owner.</h1><p>AI triage, SLA governance and capacity-aware work allocation in one system.</p></div><form className="login-form" onSubmit={submit}><label>Email</label><div className="input-wrap"><FiUser /><input value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@company.com"/></div><label>Password</label><div className="input-wrap"><FiLock /><input type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password"/></div>{error&&<div className="login-error">{error}</div>}<button>Sign in to workspace</button></form><div className="role-strip"><span><FiShield /> Admin</span><span><FiHeadphones /> Resolver</span><span><FiUser /> Customer</span></div></section></main>;
}
