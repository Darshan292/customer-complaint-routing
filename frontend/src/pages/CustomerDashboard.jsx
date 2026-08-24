import { useEffect, useMemo, useState } from "react";
import API from "../services/api";
import TicketDetailModal from "../components/TicketDetailModal";
import {
  FiAlertTriangle,
  FiCheckCircle,
  FiClock,
  FiPlus,
  FiRefreshCw,
  FiSearch,
  FiSend,
  FiShield,
  FiX,
} from "react-icons/fi";
import "./CustomerDashboard.css";

const priorities = ["Low", "Medium", "High", "Critical"];

function initials(name = "") {
  return (
    name
      .split(" ")
      .map((x) => x[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "CU"
  );
}

function active(ticket) {
  return !["RESOLVED", "CLOSED"].includes(ticket.status);
}

function slaLabel(ticket) {
  if (ticket.sla_breached) return "SLA BREACHED";
  if (ticket.remaining_seconds == null) return `${ticket.sla_hours || "—"}h SLA`;

  const minutes = Math.max(0, Math.floor(ticket.remaining_seconds / 60));
  const hours = Math.floor(minutes / 60);

  return hours ? `${hours}h remaining` : `${minutes}m remaining`;
}

export default function CustomerDashboard() {
  const user = JSON.parse(localStorage.getItem("user") || "{}");

  const [tickets, setTickets] = useState([]);
  const [text, setText] = useState("");
  const [priority, setPriority] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [detail, setDetail] = useState({ sla: null, events: [] });
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState(null);

  const notify = (type, title, message) => {
    setToast({ type, title, message });
    window.clearTimeout(window.__customerToast);
    window.__customerToast = window.setTimeout(() => setToast(null), 5500);
  };

  const load = async () => {
    try {
      const response = await API.get(
        `/tickets/customer/${encodeURIComponent(user.name)}`
      );
      setTickets(response.data || []);
    } catch (err) {
      notify(
        "error",
        "Support center unavailable",
        err.response?.data?.detail || "Unable to load your tickets."
      );
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const activeTickets = tickets.filter(active);
  const criticalTickets = activeTickets.filter(
    (ticket) => ticket.priority_level === "Critical"
  );
  const breachedTickets = activeTickets.filter(
    (ticket) => ticket.sla_breached || ticket.sla_state === "BREACHED"
  );
  const resolvedTickets = tickets.filter(
    (ticket) => ["RESOLVED", "CLOSED"].includes(ticket.status)
  );

  const visibleTickets = useMemo(() => {
    const q = search.trim().toLowerCase();

    return tickets.filter((ticket) => {
      if (filter === "ACTIVE" && !active(ticket)) return false;
      if (filter === "RESOLVED" && active(ticket)) return false;
      if (
        filter === "CRITICAL" &&
        ticket.priority_level !== "Critical"
      )
        return false;

      if (!q) return true;

      return `${ticket.id} ${ticket.summary} ${ticket.category} ${ticket.subcategory} ${ticket.status}`
        .toLowerCase()
        .includes(q);
    });
  }, [tickets, filter, search]);

  const submit = async () => {
    if (text.trim().length < 10) {
      notify(
        "error",
        "More detail required",
        "Describe the issue in at least 10 characters."
      );
      return;
    }

    setLoading(true);

    try {
      const response = await API.post(
        "/tickets/analyze-and-create",
        {
          customer_name: user.name,
          customer_tier: user.customer_tier || "Gold",
          complaint_text: text,
          priority: priority || null,
        }
      );

      const created = response.data;

      setText("");
      setPriority("");
      await load();

      const ticketId = created.ticket_id || created.ticket?.id;

      notify(
        "success",
        `Request #${ticketId || "created"} submitted`,
        created.ticket?.assigned_agent_name
          ? `Assigned to ${created.ticket.assigned_agent_name}. SLA: ${created.ticket.sla_hours}h.`
          : `Routed to ${created.ticket?.assigned_team || "the support queue"}. SLA: ${
              created.ticket?.sla_hours || "—"
            }h.`
      );

      if (ticketId) {
        const latest = (await API.get(
          `/tickets/customer/${encodeURIComponent(user.name)}`
        )).data.find((ticket) => ticket.id === ticketId);

        if (latest) {
          await openTicket(latest);
        }
      }
    } catch (err) {
      notify(
        "error",
        "Request was not submitted",
        err.response?.data?.detail ||
          "The support platform could not create your request."
      );
    } finally {
      setLoading(false);
    }
  };

  const openTicket = async (ticket) => {
    setSelectedTicket(ticket);

    try {
      const [slaResponse, eventsResponse] = await Promise.all([
        API.get(`/tickets/${ticket.id}/sla`),
        API.get(`/tickets/${ticket.id}/events`),
      ]);

      setDetail({
        sla: slaResponse.data,
        events: eventsResponse.data || [],
      });
    } catch (err) {
      notify(
        "error",
        "Ticket details unavailable",
        err.response?.data?.detail ||
          "Unable to load SLA and ticket history."
      );
    }
  };

  return (
    <div className="customer-enterprise">
      <header className="customer-topbar">
        <div className="customer-brand-block">
          <div className="customer-logo">
            <FiShield />
          </div>

          <div>
            <span className="eyebrow">CUSTOMER SUPPORT CENTER</span>
            <h1>How can we help?</h1>
            <p>
              Raise a request, track its owner and understand the SLA
              commitment in real time.
            </p>
          </div>
        </div>

        <div className="customer-top-actions">
          <button className="customer-refresh" onClick={load}>
            <FiRefreshCw /> Refresh
          </button>

          <div className="customer-profile">
            <div>{initials(user.name)}</div>
            <span>{user.name}</span>
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
          <button onClick={() => setToast(null)}>
            <FiX />
          </button>
        </div>
      )}

      <section className="customer-hero-grid">
        <div className="customer-intake-card">
          <div className="intake-kicker">
            <FiPlus /> NEW SUPPORT REQUEST
          </div>

          <h2>Tell us what happened</h2>
          <p>
            Our AI will classify the issue, assess business impact, recommend
            priority and route it to the appropriate operational team.
          </p>

          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Describe what happened, who is affected, the business impact, and what outcome you need..."
          />

          <div className="customer-intake-bottom">
            <div>
              <label>Requested priority</label>
              <select
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
              >
                <option value="">Let AI determine priority</option>
                {priorities.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </div>

            <button
              className="submit-request"
              disabled={loading}
              onClick={submit}
            >
              <FiSend />
              {loading ? "AI triage in progress..." : "Submit request"}
            </button>
          </div>

          <div className="ai-intake-note">
            <FiShield />
            <span>
              Customer-requested priority is a signal. The platform can
              increase priority when risk, sentiment or business impact
              requires it.
            </span>
          </div>
        </div>

        <div className="customer-command-card">
          <div className="card-kicker">SERVICE HEALTH</div>

          <div className="customer-stat-grid">
            <div>
              <span>Total requests</span>
              <strong>{tickets.length}</strong>
            </div>
            <div>
              <span>Active</span>
              <strong>{activeTickets.length}</strong>
            </div>
            <div className="danger">
              <span>SLA breached</span>
              <strong>{breachedTickets.length}</strong>
            </div>
            <div className="critical">
              <span>Critical</span>
              <strong>{criticalTickets.length}</strong>
            </div>
          </div>

          <div className="customer-health-line">
            <div>
              <FiCheckCircle />
              <span>Resolved / closed</span>
              <strong>{resolvedTickets.length}</strong>
            </div>
            <div>
              <FiClock />
              <span>Live tracking</span>
              <strong>ACTIVE</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="customer-requests">
        <div className="customer-list-header">
          <div>
            <span className="eyebrow">REQUEST HISTORY</span>
            <h2>Your support requests</h2>
            <p>Open any request for the full ticket record, SLA and audit history.</p>
          </div>

          <div className="customer-list-tools">
            <div className="customer-search">
              <FiSearch />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search requests..."
              />
            </div>

            {["ALL", "ACTIVE", "CRITICAL", "RESOLVED"].map((item) => (
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

        <div className="customer-ticket-grid">
          {visibleTickets.length === 0 ? (
            <div className="customer-empty">
              <FiCheckCircle />
              <h3>No requests in this view</h3>
              <p>Submit a new support request or change the filter.</p>
            </div>
          ) : (
            visibleTickets.map((ticket) => (
              <article
                className={`customer-ticket-card ${
                  ticket.priority_level?.toLowerCase() || ""
                }`}
                key={ticket.id}
                onClick={() => openTicket(ticket)}
              >
                <div className="customer-ticket-head">
                  <span>#{ticket.id}</span>

                  <span
                    className={`customer-priority ${
                      ticket.priority_level?.toLowerCase() || ""
                    }`}
                  >
                    {ticket.priority_level}
                  </span>
                </div>

                <h3>{ticket.summary || ticket.category}</h3>

                <p>
                  {ticket.category} · {ticket.subcategory}
                </p>

                <div className="customer-ticket-owner">
                  <div>
                    <span>OWNER</span>
                    <strong>
                      {ticket.assigned_agent_name ||
                        ticket.assigned_team ||
                        "Routing queue"}
                    </strong>
                  </div>

                  <div>
                    <span>STATUS</span>
                    <strong>{ticket.status?.replaceAll("_", " ")}</strong>
                  </div>
                </div>

                <div className="customer-ticket-footer">
                  <span
                    className={
                      ticket.sla_breached ? "danger-text" : ""
                    }
                  >
                    <FiClock /> {slaLabel(ticket)}
                  </span>

                  <button
                    onClick={(event) => {
                      event.stopPropagation();
                      openTicket(ticket);
                    }}
                  >
                    View details
                  </button>
                </div>
              </article>
            ))
          )}
        </div>
      </section>

      {selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          mode="customer"
          events={detail.events}
          sla={detail.sla}
          onClose={() => setSelectedTicket(null)}
        />
      )}
    </div>
  );
}
