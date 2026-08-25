import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/api";
import TicketDetailModal from "../components/TicketDetailModal";
import NotificationCenter from "../components/NotificationCenter";
import {
  FiActivity,
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiRefreshCw,
  FiShield,
  FiUser,
  FiZap,
} from "react-icons/fi";
import "./AgentDashboard.css";

const priorityRank = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
};

function slaState(ticket) {
  return ticket.sla_state || "NO_SLA";
}

function formatRemaining(ticket) {
  if (ticket.sla_breached) return "SLA BREACHED";
  if (ticket.remaining_seconds == null) return "No SLA";

  const minutes = Math.max(0, Math.floor(ticket.remaining_seconds / 60));
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  return hours > 0 ? `${hours}h ${mins}m remaining` : `${mins}m remaining`;
}

function MetricCard({ icon, label, value, tone = "" }) {
  return (
    <div className={`agent-metric ${tone}`}>
      <div className="agent-metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function AgentDashboard() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem("user") || "{}");

  const [tickets, setTickets] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [detail, setDetail] = useState({
    analysis: null,
    sla: null,
    events: [],
    resolutionRecommendation: null,
    similarTickets: [],
    resolutionContext: null,
  });
  const [aiLoading, setAiLoading] = useState(false);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);
  const [filter, setFilter] = useState("ACTIVE");
  const [search, setSearch] = useState("");

  const notify = (type, title, message) => {
    setToast({ type, title, message });
    window.clearTimeout(window.__agentToast);
    window.__agentToast = window.setTimeout(() => setToast(null), 5000);
  };

  const logout = async () => {
    try {
      await API.post("/logout");
    } catch (err) {
      console.warn("Server logout unavailable:", err);
    } finally {
      localStorage.removeItem("user");
      navigate("/");
    }
  };

  const load = async () => {
    try {
      const [ticketResponse, agentResponse] = await Promise.all([
        API.get(`/tickets/agent/${user.id}`),
        API.get("/agents"),
      ]);

      setTickets(ticketResponse.data.tickets || []);
      setProfile(
        agentResponse.data.find((agent) => agent.id === user.id) || null
      );
    } catch (err) {
      console.error(err);
      notify(
        "error",
        "Workspace unavailable",
        err.response?.data?.detail || "Unable to load resolver workspace."
      );
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = tickets.filter(
    (ticket) => !["RESOLVED", "CLOSED"].includes(ticket.status)
  ).length;

  const breachedCount = tickets.filter(
    (ticket) => slaState(ticket) === "BREACHED"
  ).length;

  const atRiskCount = tickets.filter(
    (ticket) => ticket.sla_at_risk === true || slaState(ticket) === "AT_RISK"
  ).length;

  const resolvedCount = tickets.filter((ticket) =>
    ["RESOLVED", "CLOSED"].includes(ticket.status)
  ).length;

  const visibleTickets = useMemo(() => {
    const q = search.trim().toLowerCase();

    return [...tickets]
      .filter((ticket) => {
        if (filter === "ACTIVE" && ["RESOLVED", "CLOSED"].includes(ticket.status))
          return false;
        if (filter === "SLA" && !["BREACHED", "AT_RISK"].includes(slaState(ticket)))
          return false;
        if (filter === "CRITICAL" && ticket.priority_level !== "Critical")
          return false;
        if (filter === "RESOLVED" && !["RESOLVED", "CLOSED"].includes(ticket.status))
          return false;

        if (!q) return true;

        return `${ticket.id} ${ticket.summary} ${ticket.customer_name} ${ticket.category} ${ticket.subcategory}`
          .toLowerCase()
          .includes(q);
      })
      .sort((a, b) => {
        const slaRank = {
          BREACHED: 4,
          AT_RISK: 3,
          CRITICAL: 2,
          ON_TRACK: 1,
          NO_SLA: 0,
        };

        return (
          (slaRank[slaState(b)] || 0) -
            (slaRank[slaState(a)] || 0) ||
          (priorityRank[b.priority_level] || 0) -
            (priorityRank[a.priority_level] || 0)
        );
      });
  }, [tickets, filter, search]);

  const openTicket = async (ticket) => {
    setSelectedTicket(ticket);
    setLoadingDetail(true);

    try {
      const [slaResponse, eventsResponse, similarResponse] = await Promise.all([
        API.get(`/tickets/${ticket.id}/sla`),
        API.get(`/tickets/${ticket.id}/events`),
        API.get(`/tickets/${ticket.id}/similar-resolved`),
      ]);

      setDetail({
        analysis: null,
        sla: slaResponse.data,
        events: eventsResponse.data || [],
        resolutionRecommendation: null,
        similarTickets: similarResponse.data?.tickets || [],
        resolutionContext: null,
      });
    } catch (err) {
      notify(
        "error",
        "Ticket details unavailable",
        err.response?.data?.detail || "Unable to load SLA or audit information."
      );
    } finally {
      setLoadingDetail(false);
    }
  };

  const refreshSelected = async () => {
    if (!selectedTicket) return;

    const response = await API.get(`/tickets/agent/${user.id}`);
    const latest = (response.data.tickets || []).find(
      (ticket) => ticket.id === selectedTicket.id
    );

    if (latest) {
      setSelectedTicket(latest);
      const [slaResponse, eventsResponse, similarResponse] = await Promise.all([
        API.get(`/tickets/${latest.id}/sla`),
        API.get(`/tickets/${latest.id}/events`),
        API.get(`/tickets/${latest.id}/similar-resolved`),
      ]);

      setDetail({
        analysis: null,
        sla: slaResponse.data,
        events: eventsResponse.data || [],
        resolutionRecommendation: detail.resolutionRecommendation,
        similarTickets: similarResponse.data?.tickets || [],
      });
    }
  };

  const updateStatus = async (id, status) => {
    setBusy(true);

    try {
      const response = await API.put(`/tickets/${id}/status`, { status });

      notify(
        "success",
        `Ticket #${id} updated`,
        response.data?.status
          ? `Status changed to ${response.data.status.replaceAll("_", " ")}.`
          : "Ticket status updated successfully."
      );

      await load();
      await refreshSelected();
    } catch (err) {
      notify(
        "error",
        `Ticket #${id} was not updated`,
        err.response?.data?.detail || "The status change was rejected."
      );
    } finally {
      setBusy(false);
    }
  };

  const updatePriority = async (id, priority) => {
    setBusy(true);

    try {
      const response = await API.put(`/tickets/${id}/priority`, {
        priority,
      });

      notify(
        "success",
        `Ticket #${id} priority changed`,
        `Priority is now ${response.data?.priority_level || priority}.`
      );

      await load();
      await refreshSelected();
    } catch (err) {
      notify(
        "error",
        `Priority change rejected`,
        err.response?.data?.detail || "Unable to change ticket priority."
      );
    } finally {
      setBusy(false);
    }
  };

  const escalate = async (id) => {
    const reason = window.prompt(
      "Escalation reason",
      "Resolver requires operational assistance."
    );

    if (!reason) return;

    setBusy(true);

    try {
      const response = await API.post(`/tickets/${id}/escalate`, {
        reason,
      });

      notify(
        "success",
        `Ticket #${id} escalated`,
        `Escalation level ${response.data?.escalation_level || ""} · Owner: ${
          response.data?.owner || "operations"
        }`
      );

      await load();
      await refreshSelected();
    } catch (err) {
      notify(
        "error",
        `Escalation failed`,
        err.response?.data?.detail || "Unable to escalate this ticket."
      );
    } finally {
      setBusy(false);
    }
  };


  const loadResolutionRecommendation = async (ticketId) => {
    setAiLoading(true);

    try {
      const response = await API.post(
        `/tickets/${ticketId}/ai-resolution-recommendation`
      );

      setDetail((current) => ({
        ...current,
        resolutionRecommendation:
          response.data?.recommendation || null,
      }));

      notify(
        "success",
        "AI resolution guidance ready",
        "The resolver recommendation was generated from the current ticket."
      );
    } catch (err) {
      notify(
        "error",
        "AI recommendation unavailable",
        err.response?.data?.detail ||
          "Groq could not generate a resolution recommendation."
      );
    } finally {
      setAiLoading(false);
    }
  };

  const loadResolutionContext = async (ticketId) => {
    try {
      const response = await API.get(
        `/tickets/${ticketId}/resolution-context`
      );

      setDetail((current) => ({
        ...current,
        resolutionContext: response.data || null,
      }));

      notify(
        "success",
        "Resolution context ready",
        "Historical tickets, controlled SOP guidance and KB evidence were retrieved."
      );
    } catch (err) {
      notify(
        "error",
        "Resolution context unavailable",
        err.response?.data?.detail ||
          "Unable to retrieve ticket, SOP and KB context."
      );
    }
  };

  const loadSimilarTickets = async (ticketId) => {
    setSimilarLoading(true);

    try {
      const response = await API.get(
        `/tickets/${ticketId}/similar-resolved?limit=5`
      );

      setDetail((current) => ({
        ...current,
        similarTickets: response.data?.tickets || [],
      }));

      notify(
        "success",
        "Historical cases refreshed",
        `${response.data?.count || 0} similar resolved case(s) found.`
      );
    } catch (err) {
      notify(
        "error",
        "Historical cases unavailable",
        err.response?.data?.detail ||
          "Unable to search resolved tickets."
      );
    } finally {
      setSimilarLoading(false);
    }
  };

  return (
    <div className="agent-page">
      <header className="agent-topbar">
        <div>
          <span className="eyebrow">RESOLVER OPERATIONS CENTER</span>
          <h1>My service desk</h1>
          <p>
            Your queue, SLA exposure, workforce status and ticket controls in
            one workspace.
          </p>
        </div>

        <div className="agent-top-actions">
          <NotificationCenter />
          <button className="agent-refresh" onClick={load}>
            <FiRefreshCw /> Refresh
          </button>
          <button className="agent-refresh" onClick={logout}>
            Logout
          </button>

          <div className="agent-profile-card">
            <div className="agent-avatar">
              {(user.name || "Agent")
                .split(" ")
                .map((x) => x[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </div>

            <div>
              <strong>{user.name}</strong>
              <span>{profile?.team || "Resolver"}</span>
            </div>
          </div>
        </div>
      </header>

      {toast && (
        <div className={`workspace-toast ${toast.type}`}>
          <div className="toast-mark">
            {toast.type === "success" ? <FiCheckCircle /> : <FiAlertTriangle />}
          </div>
          <div>
            <strong>{toast.title}</strong>
            <span>{toast.message}</span>
          </div>
          <button onClick={() => setToast(null)}>×</button>
        </div>
      )}

      <section className="agent-command-grid">
        <div className="agent-identity-card">
          <div className="agent-identity-head">
            <div className="agent-big-avatar">
              {(user.name || "Agent")
                .split(" ")
                .map((x) => x[0])
                .slice(0, 2)
                .join("")
                .toUpperCase()}
            </div>

            <div>
              <span className="eyebrow">CURRENT RESOLVER</span>
              <h2>{user.name}</h2>
              <p>{profile?.email}</p>
              <span className="team-label">{profile?.team}</span>
            </div>
          </div>

          <div className="agent-status-row">
            <span className={`status-pill ${profile?.availability_status?.toLowerCase()}`}>
              {profile?.availability_status || "UNKNOWN"}
            </span>
            <span>{profile?.shift_active ? "ON SHIFT" : "OFF SHIFT"}</span>
            {profile?.on_call_enabled && <span><FiShield /> ON-CALL</span>}
          </div>
        </div>

        <div className="agent-capacity-card">
          <div className="card-kicker">WORKFORCE CAPACITY</div>
          <div className="capacity-big">
            <strong>{profile?.open_tickets ?? 0}</strong>
            <span>/ {profile?.max_concurrent_tickets ?? profile?.capacity ?? 0}</span>
          </div>
          <div className="capacity-track">
            <span
              style={{
                width: `${Math.min((profile?.utilization || 0) * 100, 100)}%`,
              }}
            />
          </div>
          <div className="capacity-foot">
            <span>Utilization</span>
            <strong>{Math.round((profile?.utilization || 0) * 100)}%</strong>
          </div>
        </div>

        <div className="agent-workforce-card">
          <div className="card-kicker">WORKFORCE INTELLIGENCE</div>
          <div className="workforce-stats">
            <div><span>Experience</span><strong>{profile?.experience_years ?? "—"}y</strong></div>
            <div><span>Capacity</span><strong>{profile?.capacity ?? "—"}</strong></div>
            <div><span>Max concurrent</span><strong>{profile?.max_concurrent_tickets ?? "—"}</strong></div>
            <div><span>Eligible</span><strong>{profile?.eligible_for_assignment ? "YES" : "NO"}</strong></div>
          </div>
          <div className="skills-line">
            <FiZap /> {profile?.skills || "No skill profile recorded"}
          </div>
        </div>
      </section>

      <section className="agent-metrics">
        <MetricCard icon={<FiActivity />} label="Active tickets" value={activeCount} />
        <MetricCard icon={<FiAlertTriangle />} label="SLA breached" value={breachedCount} tone="danger" />
        <MetricCard icon={<FiClock />} label="SLA at risk" value={atRiskCount} tone="warning" />
        <MetricCard icon={<FiCheckCircle />} label="Resolved / closed" value={resolvedCount} tone="success" />
        <MetricCard
          icon={<FiShield />}
          label="Assignment readiness"
          value={profile?.eligible_for_assignment ? "READY" : "RESTRICTED"}
        />
      </section>

      <section className="agent-queue-section">
        <div className="queue-header">
          <div>
            <span className="eyebrow">PRIORITIZED WORK</span>
            <h2>My queue</h2>
            <p>Open a ticket to see its complete SLA, history and resolution controls.</p>
          </div>

          <div className="queue-tools">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search tickets..."
            />

            {["ACTIVE", "SLA", "CRITICAL", "RESOLVED", "ALL"].map((item) => (
              <button
                key={item}
                className={filter === item ? "active" : ""}
                onClick={() => setFilter(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="agent-ticket-list">
          {visibleTickets.length === 0 ? (
            <div className="agent-empty">
              <FiCheckCircle />
              <h3>No tickets match this view</h3>
              <p>Try another filter or refresh the resolver queue.</p>
            </div>
          ) : (
            visibleTickets.map((ticket) => {
              const state = slaState(ticket);

              return (
                <article
                  className={`agent-ticket-card ${state.toLowerCase()}`}
                  key={ticket.id}
                  onClick={() => openTicket(ticket)}
                >
                  <div className={`priority-strip ${ticket.priority_level?.toLowerCase()}`} />

                  <div className="ticket-main-block">
                    <div className="ticket-topline">
                      <span className="ticket-number">#{ticket.id}</span>
                      <span className={`priority-pill ${ticket.priority_level?.toLowerCase()}`}>
                        {ticket.priority_level}
                      </span>
                      <span className="status-text">
                        {ticket.status?.replaceAll("_", " ")}
                      </span>
                    </div>

                    <h3>{ticket.summary || ticket.category}</h3>

                    <p>
                      {ticket.customer_name} · {ticket.category} ·{" "}
                      {ticket.subcategory}
                    </p>
                  </div>

                  <div className="ticket-sla-block">
                    <span>SLA</span>
                    <strong className={state === "BREACHED" ? "danger-text" : ""}>
                      {formatRemaining(ticket)}
                    </strong>
                  </div>

                  <div className="ticket-action-block">
                    {state === "BREACHED" && (
                      <span className="risk-label danger-text">BREACHED</span>
                    )}
                    {state === "AT_RISK" && (
                      <span className="risk-label warning-text">AT RISK</span>
                    )}
                    <button
                      onClick={(event) => {
                        event.stopPropagation();
                        openTicket(ticket);
                      }}
                    >
                      Open ticket
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>

      {selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          mode="agent"
          events={detail.events}
          sla={detail.sla}
          loading={busy || loadingDetail}
          onClose={() => setSelectedTicket(null)}
          onStatus={updateStatus}
          onPriority={updatePriority}
          onEscalate={escalate}
          resolutionRecommendation={detail.resolutionRecommendation}
          similarTickets={detail.similarTickets}
          resolutionContext={detail.resolutionContext}
          aiLoading={aiLoading}
          similarLoading={similarLoading}
          onLoadResolutionRecommendation={loadResolutionRecommendation}
          onLoadSimilarTickets={loadSimilarTickets}
          onLoadResolutionContext={loadResolutionContext}
        />
      )}
    </div>
  );
}
