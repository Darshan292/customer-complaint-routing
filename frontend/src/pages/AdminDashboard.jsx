import { useEffect, useMemo, useState } from "react";
import API from "../services/api";
import {
  FiActivity, FiAlertOctagon, FiAlertTriangle, FiBarChart2, FiBell, FiCheckCircle,
  FiChevronRight, FiClock, FiCpu, FiDatabase, FiEdit3, FiRefreshCw, FiSearch,
  FiShield, FiSliders, FiUserCheck, FiUsers, FiUserPlus, FiZap, FiX,
} from "react-icons/fi";
import TicketDetailModal from "../components/TicketDetailModal";
import "./AdminDashboard.css";

const ACTIVE = ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER"];
const STATUS = ["AVAILABLE", "BUSY", "AWAY", "OFFLINE", "ON_LEAVE"];

const initials = (name = "") => name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase() || "??";

function priorityClass(value = "") { return value.toLowerCase(); }

export default function AdminDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentWorkforce, setAgentWorkforce] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [events, setEvents] = useState([]);
  const [sla, setSla] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [report, setReport] = useState(null);
  const [search, setSearch] = useState("");
  const [queueFilter, setQueueFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [showAgentForm, setShowAgentForm] = useState(false);

  const notify = (type, title, body) => {
    setNotice({ type, title, body });
    window.setTimeout(() => setNotice(null), 6500);
  };

  const load = async () => {
    try {
      setLoading(true);
      const [d, t, a] = await Promise.all([
        API.get("/tickets/dashboard"),
        API.get("/tickets"),
        API.get("/agents"),
      ]);
      setDashboard(d.data);
      setTickets(t.data || []);
      setAgents(a.data || []);
      setError("");
    } catch (err) {
      const message = err?.response?.data?.detail || "Unable to load operations data.";
      setError(message);
      notify("error", "Operations data unavailable", message);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, []);

  const openTicket = async (ticket) => {
    try {
      setSelectedTicket(ticket);
      setAnalysis(null); setEvents([]); setSla(null);
      const [a, e, s] = await Promise.all([
        API.get(`/tickets/${ticket.id}/assignment-analysis`),
        API.get(`/tickets/${ticket.id}/events`),
        API.get(`/tickets/${ticket.id}/sla`),
      ]);
      setAnalysis(a.data); setEvents(e.data || []); setSla(s.data);
    } catch (err) {
      const message = err?.response?.data?.detail || "Unable to load ticket intelligence.";
      setError(message); notify("error", `Ticket #${ticket.id}`, message);
    }
  };

  const refreshSelectedTicket = async (ticketId) => {
    const updated = (await API.get("/tickets")).data.find((t) => t.id === ticketId);
    if (updated) await openTicket(updated);
  };

  const runAction = async (action, successTitle, successBody, reload = true) => {
    try {
      setActionLoading(true); setError("");
      const response = await action();
      notify("success", successTitle, successBody || "Operation completed successfully.");
      if (reload) await load();
      return response;
    } catch (err) {
      const message = err?.response?.data?.detail || err?.response?.data?.message || "Operation failed.";
      setError(message); notify("error", "Operation failed", message); throw err;
    } finally { setActionLoading(false); }
  };

  const autoAssignAll = async () => {
    try {
      setActionLoading(true); setError("");
      const response = await API.post("/tickets/auto-assign-unassigned");
      setReport({ type: "assignment", data: response.data });
      const firstSkipped = (response.data.results || []).find((item) =>
        String(item.status || "").toUpperCase() === "SKIPPED"
      );
      const bulkMessage = response.data.assigned > 0
        ? `${response.data.assigned} assigned · ${response.data.skipped} skipped${firstSkipped?.reason ? ` · ${firstSkipped.reason}` : ""}`
        : `${response.data.skipped} ticket(s) require manual assignment${firstSkipped?.reason ? ` · ${firstSkipped.reason}` : ""}`;

      notify(
        response.data.assigned > 0 ? "success" : "warning",
        response.data.assigned > 0 ? "Automatic routing completed" : "Manual assignment required",
        bulkMessage,
      );
      await load();
    } catch (err) {
      const message = err?.response?.data?.detail || "Bulk assignment failed.";
      setError(message); notify("error", "Automatic routing failed", message);
    } finally { setActionLoading(false); }
  };

  const autoAssign = async (id) => {
    try {
      setActionLoading(true);
      setError("");

      const response = await API.post(`/tickets/${id}/auto-assign`);
      const data = response?.data || {};

      // Do not hide the routing engine's actual decision. The backend may
      // return either an assigned ticket or a diagnostic skip response.
      const skipped =
        String(data.status || "").toUpperCase() === "SKIPPED" ||
        String(data.status || "").toUpperCase() === "FAILED" ||
        data.assigned === false ||
        !data.assigned_agent_id &&
        !data.assigned_agent_name &&
        Boolean(data.reason || data.message);

      if (skipped) {
        const reason =
          data.reason ||
          data.message ||
          data.assignment_explanation ||
          "No eligible resolver was available for automatic assignment.";

        const teamText = data.resolved_team
          ? `${data.original_team || "Current team"} → ${data.resolved_team}`
          : data.assigned_team
            ? `Team: ${data.assigned_team}`
            : "";

        notify(
          "warning",
          `Ticket #${id} requires manual assignment`,
          `${teamText ? `${teamText}. ` : ""}${reason}`,
        );

        setReport({
          type: "assignment",
          data: {
            total_unassigned: 1,
            assigned: 0,
            skipped: 1,
            results: [{
              ticket_id: id,
              status: "SKIPPED",
              original_team: data.original_team || data.assigned_team,
              resolved_team: data.resolved_team,
              reason,
            }],
          },
        });
      } else {
        const resolver = data.assigned_agent_name || data.agent_name || data.assigned_agent_id;
        const explanation =
          data.assignment_explanation ||
          data.explanation ||
          (resolver ? `Assigned to ${resolver}.` : "Automatic assignment completed.");

        notify(
          "success",
          `Ticket #${id} automatically assigned`,
          explanation,
        );
      }

      await load();
      await refreshSelectedTicket(id);
      return response;
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.reason ||
        err?.response?.data?.message ||
        "Automatic assignment failed.";
      setError(message);
      notify("error", `Ticket #${id} automatic routing failed`, message);
    } finally {
      setActionLoading(false);
    }
  };

  const assign = async (id, agentId) => {
    try {
      await runAction(() => API.put(`/tickets/${id}/assign`, { agent_id: agentId }), `Ticket #${id} assigned`, "Manual assignment recorded. The resolver can now start work from their queue.");
      await refreshSelectedTicket(id);
    } catch { /* notification already rendered */ }
  };

  const updatePriority = async (id, priority) => { await runAction(() => API.put(`/tickets/${id}/priority`, { priority }), `Ticket #${id} priority updated`, `Priority is now ${priority}.`); await refreshSelectedTicket(id); };
  const updateStatus = async (id, status) => { await runAction(() => API.put(`/tickets/${id}/status`, { status }), `Ticket #${id} status updated`, `Lifecycle state changed to ${status.replaceAll("_", " ")}.`); await refreshSelectedTicket(id); };

  const escalate = async (id) => {
    const reason = window.prompt("Escalation reason:", "Operational attention required.");
    if (!reason) return;
    await runAction(() => API.post(`/tickets/${id}/escalate`, { reason }), `Ticket #${id} escalated`, "The escalation has been recorded and the ticket is now under elevated operational attention.");
    await refreshSelectedTicket(id);
  };

  const runSla = async () => {
    await runAction(() => API.post("/tickets/run-sla-monitor"), "SLA monitor completed", "SLA exposure and escalation rules were evaluated across the queue.");
  };

  const selectAgent = async (agent) => {
    setSelectedAgent(agent);
    try {
      const response = await API.get(`/agents/${agent.id}/workforce`);
      setAgentWorkforce(response.data);
    } catch (err) {
      notify("error", "Resolver workforce unavailable", err?.response?.data?.detail || "Could not load resolver workforce details.");
      setAgentWorkforce(null);
    }
  };

  const changeAgentStatus = async (agentId, status) => {
    await runAction(() => API.put(`/agents/${agentId}/status`, { availability_status: status }), "Resolver status updated", `Availability changed to ${status.replaceAll("_", " ")}.`);
    if (selectedAgent?.id === agentId) await selectAgent((await API.get("/agents")).data.find((a) => a.id === agentId));
  };

  const changeCapacity = async (agentId, value) => {
    await runAction(() => API.put(`/agents/${agentId}/capacity`, { max_concurrent_tickets: Number(value) }), "Resolver capacity updated", "Concurrent ticket capacity has been updated.");
  };

  const toggleOnCall = async (agentId, enabled) => {
    await runAction(() => API.put(`/agents/${agentId}/on-call`, { on_call_enabled: enabled }), "On-call coverage updated", enabled ? "Resolver is now part of emergency coverage." : "On-call coverage has been disabled.");
  };

  const saveSchedule = async (agent) => {
    await runAction(() => API.put(`/agents/${agent.id}/schedule`, { timezone: agent.timezone, shift_start: agent.shift_start, shift_end: agent.shift_end, work_days: agent.work_days }), "Schedule updated", "Resolver shift and working calendar were saved.");
  };

  const createAgent = async (payload) => {
    await runAction(() => API.post("/agents", payload), "Resolver created", `${payload.name} has been added to ${payload.team}.`);
    setShowAgentForm(false);
  };

  const filteredTickets = useMemo(() => tickets.filter((ticket) => {
    const haystack = `${ticket.id} ${ticket.customer_name || ""} ${ticket.summary || ""} ${ticket.category || ""} ${ticket.assigned_team || ""} ${ticket.assigned_agent_name || ""}`.toLowerCase();
    if (search && !haystack.includes(search.toLowerCase())) return false;
    if (queueFilter === "UNASSIGNED" && ticket.assigned_agent_id) return false;
    if (queueFilter === "ASSIGNED" && !ticket.assigned_agent_id) return false;
    if (queueFilter === "ACTIVE" && !ACTIVE.includes(ticket.status)) return false;
    if (queueFilter === "SLA" && !ticket.sla_breached) return false;
    if (queueFilter === "ESCALATED" && !ticket.escalation_required) return false;
    if (queueFilter === "RESOLVED" && !["RESOLVED", "CLOSED"].includes(ticket.status)) return false;
    if (priorityFilter !== "ALL" && ticket.priority_level !== priorityFilter) return false;
    return true;
  }), [tickets, search, queueFilter, priorityFilter]);

  if (loading && !dashboard) return <div className="enterprise-loading"><FiRefreshCw className="spin" /><strong>Loading Operations Control Center</strong><span>Synchronizing tickets, SLA exposure and workforce intelligence.</span></div>;
  if (!dashboard) return <div className="admin-shell"><div className="admin-error">{error || "No dashboard data available."}</div></div>;

  const summary = dashboard.workforce_summary || {};
  const active = dashboard.open + dashboard.in_progress + dashboard.pending_customer;

  return (
    <div className="admin-shell">
      {notice && <div className={`toast ${notice.type}`}><div className="toast-icon">{notice.type === "success" ? <FiCheckCircle /> : notice.type === "error" ? <FiAlertTriangle /> : <FiBell />}</div><div><strong>{notice.title}</strong><span>{notice.body}</span></div><button onClick={() => setNotice(null)}><FiX /></button></div>}

      <header className="admin-topbar">
        <div className="brand-block"><div className="brand-mark"><FiCpu /></div><div><div className="admin-eyebrow">ENTERPRISE SERVICE OPERATIONS</div><h1>Complaint Operations Center</h1><p>AI routing · workforce orchestration · SLA command · operational control</p></div></div>
        <div className="top-actions"><span className="live-indicator"><i /> LIVE</span><button className="top-btn" onClick={load}><FiRefreshCw /> Refresh</button><button className="top-btn primary" disabled={actionLoading} onClick={autoAssignAll}><FiZap /> Auto-route queue</button></div>
      </header>

      {error && <div className="admin-error"><FiAlertTriangle /><span>{error}</span><button onClick={() => setError("")}><FiX /></button></div>}

      <main>
        <section className="hero-metrics">
          <MetricCard label="Total tickets" value={dashboard.total} icon={<FiDatabase />} sub={`${active} currently active`} />
          <MetricCard label="SLA breaches" value={dashboard.sla_breached} icon={<FiAlertOctagon />} danger sub={`${dashboard.sla_at_risk} currently at risk`} />
          <MetricCard label="Unassigned" value={dashboard.unassigned} icon={<FiUsers />} warning sub={`${summary.eligible || 0} resolvers eligible`} />
          <MetricCard label="Escalated" value={dashboard.escalated} icon={<FiAlertTriangle />} danger sub={`L2: ${dashboard.escalation_levels?.level_2 || 0}`} />
          <MetricCard label="Resolver coverage" value={`${summary.eligible || 0}/${summary.total_agents || 0}`} icon={<FiShield />} sub={`${summary.at_capacity || 0} at capacity`} />
        </section>

        <section className="command-grid">
          <div className="command-card sla-command"><div className="command-icon"><FiClock /></div><div><span>SLA COMMAND</span><strong>{dashboard.sla_breached} breached</strong><p>Run the monitor to recalculate exposure and escalation.</p></div><button onClick={runSla} disabled={actionLoading}>Run monitor <FiChevronRight /></button></div>
          <div className="command-card routing-command"><div className="command-icon"><FiZap /></div><div><span>ROUTING ENGINE</span><strong>{dashboard.unassigned} waiting</strong><p>AI weighs skills, capacity, experience, priority load and SLA health.</p></div><button onClick={autoAssignAll} disabled={actionLoading}>Route queue <FiChevronRight /></button></div>
          <div className="command-card workforce-command"><div className="command-icon"><FiUsers /></div><div><span>WORKFORCE</span><strong>{summary.eligible || 0} eligible</strong><p>{summary.available || 0} available · {summary.busy || 0} busy · {summary.at_capacity || 0} capacity risk</p></div><button onClick={() => document.getElementById("workforce")?.scrollIntoView({ behavior: "smooth" })}>Manage <FiChevronRight /></button></div>
        </section>

        <section className="main-grid" id="workforce">
          <section className="surface workforce-surface">
            <div className="surface-heading"><div><span className="section-kicker">WORKFORCE COMMAND</span><h2>Resolver capacity</h2><p>Real-time staffing, workload and emergency coverage.</p></div><button className="add-btn" onClick={() => setShowAgentForm(true)}><FiUserPlus /> Add resolver</button></div>
            <div className="resolver-grid">
              {(dashboard.workforce || []).map((agent) => (
                <button key={agent.id} className={`resolver-card ${selectedAgent?.id === agent.id ? "selected" : ""}`} onClick={() => selectAgent(agent)}>
                  <div className="resolver-card-top"><div className="person"><div className="person-avatar">{initials(agent.name)}</div><div><strong>{agent.name}</strong><span>{agent.team}</span></div></div><span className={`availability ${agent.status.toLowerCase()}`}><i />{agent.status.replaceAll("_", " ")}</span></div>
                  <div className="resolver-stats"><div><span>WORKLOAD</span><strong>{agent.open_tickets}/{agent.capacity}</strong></div><div><span>UTILIZATION</span><strong>{Math.round(agent.utilization * 100)}%</strong></div><div><span>EXPERIENCE</span><strong>{agent.experience_years}y</strong></div></div>
                  <div className="workload-bar"><span style={{ width: `${Math.min(agent.utilization * 100, 100)}%` }} /></div>
                  <div className="resolver-tags"><span>{agent.shift_active ? "ON SHIFT" : "OFF SHIFT"}</span>{agent.on_call_enabled && <span>ON-CALL</span>}{agent.sla_breaches > 0 && <span className="danger-tag">{agent.sla_breaches} SLA</span>}</div>
                </button>
              ))}
            </div>
            {selectedAgent && (
              <ResolverPanel
                agent={selectedAgent}
                workforce={agentWorkforce}
                onStatus={changeAgentStatus}
                onCapacity={changeCapacity}
                onCall={toggleOnCall}
                onSchedule={saveSchedule}
                onClose={() => {
                  setSelectedAgent(null);
                  setAgentWorkforce(null);
                }}
              />
            )}
          </section>
        </section>

        <section className="surface queue-surface">
          <div className="surface-heading queue-heading"><div><span className="section-kicker">TICKET COMMAND CENTER</span><h2>Operational queue</h2><p>Every ticket is actionable. Open a ticket for AI routing, SLA, timeline and assignment controls.</p></div><div className="queue-toolbar"><div className="search-box"><FiSearch /><input placeholder="Search ticket, customer, resolver..." value={search} onChange={(e) => setSearch(e.target.value)} /></div><select value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)}><option value="ALL">All tickets</option><option value="UNASSIGNED">Unassigned</option><option value="ASSIGNED">Assigned</option><option value="ACTIVE">Active</option><option value="SLA">SLA breached</option><option value="ESCALATED">Escalated</option><option value="RESOLVED">Resolved / closed</option></select><select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}><option value="ALL">All priorities</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></div></div>
          <div className="queue-header"><span>Ticket</span><span>Customer / issue</span><span>Priority</span><span>Ownership</span><span>SLA</span><span /></div>
          <div className="queue-list">
            {filteredTickets.map((ticket) => <button className="queue-item" key={ticket.id} onClick={() => openTicket(ticket)}><div className="ticket-number">#{ticket.id}<small>{ticket.status.replaceAll("_", " ")}</small></div><div className="ticket-summary"><strong>{ticket.summary || ticket.complaint_text?.slice(0, 80) || "Complaint"}</strong><span>{ticket.customer_name} · {ticket.assigned_team}</span></div><span className={`priority-badge ${priorityClass(ticket.priority_level)}`}>{ticket.priority_level}</span><div className="ownership"><div className="mini-avatar">{ticket.assigned_agent_name ? initials(ticket.assigned_agent_name) : "?"}</div><span>{ticket.assigned_agent_name || "UNASSIGNED"}</span></div><div className={`sla-pill ${ticket.sla_breached ? "breached" : ticket.sla_at_risk ? "risk" : "healthy"}`}>{ticket.sla_breached ? "BREACHED" : ticket.sla_at_risk ? "AT RISK" : "ON TRACK"}</div><FiChevronRight className="queue-arrow" /></button>)}
            {!filteredTickets.length && <div className="queue-empty"><FiCheckCircle /><strong>No tickets match the current view.</strong></div>}
          </div>
        </section>

        <section className="bottom-grid">
          <div className="surface analytics-surface"><div className="surface-heading"><div><span className="section-kicker">QUEUE HEALTH</span><h2>Operational distribution</h2></div></div><div className="health-grid"><HealthBlock label="Open" value={dashboard.open} total={dashboard.total} /><HealthBlock label="In progress" value={dashboard.in_progress} total={dashboard.total} /><HealthBlock label="Pending customer" value={dashboard.pending_customer} total={dashboard.total} /><HealthBlock label="Resolved" value={dashboard.resolved} total={dashboard.total} /></div></div>
          <div className="surface team-surface"><div className="surface-heading"><div><span className="section-kicker">TEAM CAPACITY</span><h2>Routing coverage</h2></div></div><div className="team-list">{(dashboard.teams || []).map((team) => <div className="team-row" key={team.team}><div><strong>{team.team}</strong><span>{team.eligible_agents}/{team.agents} eligible</span></div><div className="team-bar"><span style={{ width: `${team.agents ? Math.min((team.eligible_agents / team.agents) * 100, 100) : 0}%` }} /></div><b>{team.tickets}</b></div>)}</div></div>
        </section>
      </main>

      {selectedTicket && <TicketDetailModal ticket={selectedTicket} analysis={analysis} events={events} sla={sla} agents={agents} loading={actionLoading} mode="admin" onClose={() => { setSelectedTicket(null); setAnalysis(null); setEvents([]); setSla(null); }} onAssign={assign} onAutoAssign={autoAssign} onPriority={updatePriority} onStatus={updateStatus} onEscalate={escalate} />}
      {/* {report && <AssignmentReport report={report} onClose={() => setReport(null)} />} */}
      {showAgentForm && <AgentForm onClose={() => setShowAgentForm(false)} onCreate={createAgent} />}
    </div>
  );
}

function MetricCard({ label, value, icon, sub, danger, warning }) { return <div className={`hero-metric ${danger ? "danger" : ""} ${warning ? "warning" : ""}`}><div className="metric-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{sub}</small></div></div>; }
function HealthBlock({ label, value, total }) { const pct = total ? Math.round((value / total) * 100) : 0; return <div className="health-block"><div><span>{label}</span><strong>{value}</strong></div><div className="health-bar"><span style={{ width: `${pct}%` }} /></div><small>{pct}% of total volume</small></div>; }

function ResolverPanel({
  agent,
  workforce,
  onStatus,
  onCapacity,
  onCall,
  onSchedule,
  onClose,
}) {
  const [schedule, setSchedule] = useState({ ...agent });

  useEffect(() => {
    setSchedule({ ...agent });
  }, [agent]);

  const handleClose = () => {
    if (typeof onClose === "function") {
      onClose();
    }
  };

  return (
    <div
      className="resolver-modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          handleClose();
        }
      }}
    >
      <div
        className="resolver-modal"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="resolver-modal-header">
          <span className="section-kicker">
            RESOLVER MANAGEMENT
          </span>

          <button
            type="button"
            className="resolver-modal-close"
            onClick={handleClose}
            aria-label="Close resolver management"
            title="Close"
          >
            ×
          </button>
        </div>

        <div className="resolver-panel">
          <div className="resolver-panel-head">
            <div className="person">
              <div className="person-avatar large">
                {initials(agent.name)}
              </div>

              <div>
                <span className="section-kicker">
                  SELECTED RESOLVER
                </span>

                <h3>{agent.name}</h3>

                <p>
                  {agent.email} · {agent.team}
                </p>
              </div>
            </div>

            <div className="resolver-panel-score">
              <span>UTILIZATION</span>

              <strong>
                {Math.round(agent.utilization * 100)}%
              </strong>
            </div>
          </div>

          <div className="resolver-panel-grid">
            <div>
              <label>Availability</label>

              <div className="status-chips">
                {STATUS.map((s) => (
                  <button
                    type="button"
                    className={
                      agent.status === s ? "active" : ""
                    }
                    key={s}
                    onClick={() =>
                      onStatus(agent.id, s)
                    }
                  >
                    {s.replaceAll("_", " ")}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label>Capacity</label>

              <div className="capacity-line">
                <input
                  type="number"
                  min="1"
                  max="100"
                  defaultValue={agent.capacity}
                  onBlur={(e) =>
                    onCapacity(
                      agent.id,
                      e.target.value
                    )
                  }
                />

                <span>
                  {agent.open_tickets} active tickets ·{" "}
                  {agent.max_concurrent_tickets ??
                    agent.capacity}{" "}
                  max
                </span>
              </div>
            </div>

            <div>
              <label>Emergency coverage</label>

              <button
                type="button"
                className={`oncall ${
                  agent.on_call_enabled
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  onCall(
                    agent.id,
                    !agent.on_call_enabled
                  )
                }
              >
                <FiShield />

                {agent.on_call_enabled
                  ? "ON-CALL ENABLED"
                  : "ENABLE ON-CALL"}
              </button>
            </div>

            <div>
              <label>Workforce diagnostics</label>

              <div className="diagnostic-line">
                <strong>
                  {workforce?.summary?.active_tickets ??
                    agent.open_tickets}
                </strong>

                <span>
                  active tickets ·{" "}
                  {workforce?.summary?.sla_breached ??
                    agent.sla_breaches}{" "}
                  SLA breaches
                </span>
              </div>
            </div>
          </div>

          <div className="schedule-row">
            <div>
              <label>Shift start</label>

              <input
                value={schedule.shift_start || ""}
                onChange={(e) =>
                  setSchedule({
                    ...schedule,
                    shift_start: e.target.value,
                  })
                }
              />
            </div>

            <div>
              <label>Shift end</label>

              <input
                value={schedule.shift_end || ""}
                onChange={(e) =>
                  setSchedule({
                    ...schedule,
                    shift_end: e.target.value,
                  })
                }
              />
            </div>

            <div>
              <label>Timezone</label>

              <input
                value={
                  schedule.timezone ||
                  "Asia/Kolkata"
                }
                onChange={(e) =>
                  setSchedule({
                    ...schedule,
                    timezone: e.target.value,
                  })
                }
              />
            </div>

            <div>
              <label>Work days</label>

              <input
                value={
                  schedule.work_days ||
                  "0,1,2,3,4"
                }
                onChange={(e) =>
                  setSchedule({
                    ...schedule,
                    work_days: e.target.value,
                  })
                }
              />
            </div>

            <button
              type="button"
              onClick={() =>
                onSchedule(schedule)
              }
            >
              Save schedule
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// function AssignmentReport({ report, onClose }) {
//   const result = report.data || {};
//   // return <div className="report-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><div className="report-modal"><div className="report-head"><div><span className="section-kicker">AUTOMATION EXECUTION REPORT</span><h2>Queue routing result</h2><p>The routing engine response is shown exactly as operational feedback.</p></div><button onClick={onClose}><FiX /></button></div><div className="report-kpis"><div><strong>{result.total_unassigned ?? 0}</strong><span>processed</span></div><div className="good"><strong>{result.assigned ?? 0}</strong><span>assigned</span></div><div className="bad"><strong>{result.skipped ?? 0}</strong><span>skipped</span></div></div><div className="report-results">{(result.results || []).map((item) => <div className={`report-row ${item.status === "ASSIGNED" ? "assigned" : "skipped"}`} key={item.ticket_id}><div className="report-status">{item.status === "ASSIGNED" ? <FiCheckCircle /> : <FiAlertTriangle />}</div><div><strong>Ticket #{item.ticket_id} · {item.status}</strong><span>{item.original_team ? `${item.original_team} → ${item.resolved_team || "—"}` : item.agent_name || ""}</span><small>{item.reason || (item.agent_name ? `Assigned to ${item.agent_name}.` : "")}</small></div></div>)}</div><button className="report-close" onClick={onClose}>Done</button></div></div>;
// }

function AgentForm({ onClose, onCreate }) {
  const [form, setForm] = useState({ name: "", email: "", team: "Technical Support", role: "agent", skills: "technical", experience_years: 1, capacity: 5, max_concurrent_tickets: 5, timezone: "Asia/Kolkata", shift_start: "09:00", shift_end: "18:00", work_days: "0,1,2,3,4", auto_assignment_enabled: true, on_call_enabled: false });
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));
  return <div className="report-backdrop"><div className="agent-form"><div className="report-head"><div><span className="section-kicker">WORKFORCE MANAGEMENT</span><h2>Add resolver</h2><p>Create a resolver profile for routing and capacity planning.</p></div><button onClick={onClose}><FiX /></button></div><div className="form-grid">{[["name","Name"],["email","Email"],["skills","Skills"],["experience_years","Experience years"],["capacity","Capacity"],["max_concurrent_tickets","Max concurrent"],["timezone","Timezone"],["shift_start","Shift start"],["shift_end","Shift end"],["work_days","Work days"]].map(([key,label]) => <label key={key}>{label}<input type={key.includes("years") || key === "capacity" || key === "max_concurrent_tickets" ? "number" : "text"} value={form[key]} onChange={(e) => set(key, e.target.value)} /></label>)}<label>Team<select value={form.team} onChange={(e) => set("team", e.target.value)}>{["Technical Support","Finance Operations","Fraud Investigation","Cyber Security","Site Reliability"].map((t) => <option key={t}>{t}</option>)}</select></label></div><div className="form-toggles"><label><input type="checkbox" checked={form.auto_assignment_enabled} onChange={(e) => set("auto_assignment_enabled", e.target.checked)} /> Auto-assignment eligible</label><label><input type="checkbox" checked={form.on_call_enabled} onChange={(e) => set("on_call_enabled", e.target.checked)} /> On-call coverage</label></div><button className="top-btn primary create-btn" onClick={() => onCreate({ ...form, experience_years: Number(form.experience_years), capacity: Number(form.capacity), max_concurrent_tickets: Number(form.max_concurrent_tickets) })}><FiUserPlus /> Create resolver</button></div></div>;
}
