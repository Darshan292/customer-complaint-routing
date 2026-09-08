import { useEffect, useMemo, useState } from "react";
import {
  FiAlertTriangle,
  FiArrowRight,
  FiCheckCircle,
  FiClock,
  FiCpu,
  FiPlay,
  FiPause,
  FiShield,
  FiUser,
  FiUserCheck,
  FiHelpCircle,
  FiRefreshCw,
  FiBookOpen,
  FiX,
  FiZap,
} from "react-icons/fi";
import "./TicketDetailModal.css";

const STATUS_OPTIONS = ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "RESOLVED"];
const PRIORITIES = ["Low", "Medium", "High", "Critical"];

function initials(name = "") {
  return name.split(" ").map((x) => x[0]).slice(0, 2).join("").toUpperCase() || "??";
}

function normalizeTeam(team = "") {
  const value = team.trim().toLowerCase();
  const aliases = {
    "general support": "Technical Support",
    "technical support team": "Technical Support",
    "finance team": "Finance Operations",
    "finance operations team": "Finance Operations",
    "fraud investigation team": "Fraud Investigation",
    "cyber security team": "Cyber Security",
    "site reliability team": "Site Reliability",
  };
  return aliases[value] || team;
}

function resolveTeam(ticket, analysis) {
  const original = analysis?.ticket?.assigned_team || ticket.assigned_team || "";
  const category = `${ticket.category || ""} ${ticket.subcategory || ""}`.toLowerCase();
  if (original.toLowerCase() === "general support") {
    if (/fraud|unauthorized payment|suspicious transaction|transaction/.test(category)) return "Fraud Investigation";
    if (/privacy|personal information|security|account compromise|unauthorized access/.test(category)) return "Cyber Security";
    if (/billing|payment|refund|subscription|invoice|charge/.test(category)) return "Finance Operations";
    if (/outage|availability|infrastructure|unavailable/.test(category)) return "Site Reliability";
    return "Technical Support";
  }
  return normalizeTeam(original);
}

function scoreTone(score) {
  if (score >= 80) return "good";
  if (score >= 60) return "warn";
  return "bad";
}

function StateBadge({ children, tone = "neutral" }) {
  return <span className={`td-badge ${tone}`}>{children}</span>;
}

function Metric({ label, value }) {
  const number = Number(value ?? 0);
  return (
    <div className="td-metric">
      <div className="td-metric-top"><span>{label}</span><strong>{Math.round(number)}</strong></div>
      <div className="td-meter"><span style={{ width: `${Math.max(0, Math.min(number, 100))}%` }} /></div>
    </div>
  );
}

export default function TicketDetailModal({
  ticket,
  analysis,
  events,
  sla,
  agents = [],
  loading = false,
  mode = "admin",
  onClose,
  onAssign,
  onAutoAssign,
  onPriority,
  onStatus,
  onEscalate,
  resolutionRecommendation = null,
  similarTickets = [],
  resolutionContext = null,
  aiLoading = false,
  similarLoading = false,
  onLoadResolutionRecommendation,
  onLoadSimilarTickets,
  onLoadResolutionContext,
  onLaunchCostCenterEib,
}) {
  const [manualAgentId, setManualAgentId] = useState("");
  const [manualConfirm, setManualConfirm] = useState(false);
  const [showAiHelp, setShowAiHelp] = useState(false);
  const [showResolutionContext, setShowResolutionContext] = useState(false);

  const operationalTeam = useMemo(() => resolveTeam(ticket, analysis), [ticket, analysis]);
  const candidates = analysis?.candidates || [];

  const manualAgents = useMemo(() => {
    return agents.filter((agent) => {
      if (!agent.active) return false;
      return normalizeTeam(agent.team).toLowerCase() === operationalTeam.toLowerCase();
    });
  }, [agents, operationalTeam]);

  const selectedManualAgent = manualAgents.find((a) => String(a.id) === String(manualAgentId));
  const atCapacity = selectedManualAgent && Number(selectedManualAgent.open_tickets || 0) >= Number(selectedManualAgent.max_concurrent_tickets || selectedManualAgent.capacity || 0);

  useEffect(() => {
    setManualAgentId("");
    setManualConfirm(false);
  }, [ticket?.id]);

  if (!ticket) return null;

  const active = ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER"].includes(ticket.status);
  const slaBreached = sla?.breached || sla?.resolution?.breached || sla?.first_response?.breached;
  const selected = analysis?.selected;

  const assignManual = () => {
    if (!selectedManualAgent) return;
    if (atCapacity && !manualConfirm) {
      setManualConfirm(true);
      return;
    }
    onAssign(ticket.id, selectedManualAgent.id);
    setManualConfirm(false);
  };

  return (
    <div className="td-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="td-drawer" role="dialog" aria-modal="true">
        <div className="td-header">
          <div>
            <div className="td-eyebrow">TICKET COMMAND CENTER · #{ticket.id}</div>
            <h2>{ticket.summary || ticket.category || "Complaint"}</h2>
            <div className="td-subline">
              <StateBadge tone={ticket.priority_level?.toLowerCase()}>{ticket.priority_level || "Unknown"}</StateBadge>
              <StateBadge>{ticket.status?.replaceAll("_", " ")}</StateBadge>
              <StateBadge>{operationalTeam}</StateBadge>
            </div>
          </div>
          <button className="td-icon-button" onClick={onClose}><FiX /></button>
        </div>

        <div className="td-body">
          <section className="td-hero-grid">
            <div className="td-card customer-card">
              <div className="td-card-label"><FiUser /> CUSTOMER</div>
              <div className="td-person"><div className="td-avatar">{initials(ticket.customer_name)}</div><div><strong>{ticket.customer_name || "Unknown customer"}</strong><span>{ticket.customer_tier || "Standard"} customer</span></div></div>
              <div className="td-info-grid">
                <div><span>Category</span><strong>{ticket.category || "—"}</strong></div>
                <div><span>Subcategory</span><strong>{ticket.subcategory || "—"}</strong></div>
                <div><span>Sentiment</span><strong>{ticket.sentiment || "—"}</strong></div>
                <div><span>Business impact</span><strong>{ticket.business_impact || "—"}</strong></div>
              </div>
            </div>

            <div className={`td-card sla-card ${slaBreached ? "breached" : ""}`}>
              <div className="td-card-label"><FiClock /> SLA COMMAND</div>
              <div className="td-sla-state">{sla?.state || sla?.resolution?.state || "UNKNOWN"}</div>
              <div className="td-sla-time">{sla?.remaining_hours != null ? `${Number(sla.remaining_hours).toFixed(1)}h` : sla?.resolution?.remaining_hours != null ? `${Number(sla.resolution.remaining_hours).toFixed(1)}h` : "—"}</div>
              <div className="td-sla-label">remaining resolution time</div>
              <div className="td-info-grid compact"><div><span>Deadline</span><strong>{sla?.deadline || sla?.resolution?.deadline || ticket.sla_deadline || "—"}</strong></div><div><span>SLA hours</span><strong>{ticket.sla_hours || "—"}h</strong></div></div>
            </div>
          </section>

          <section className="td-card description-card">
            <div className="td-card-label"><FiShield /> CUSTOMER STATEMENT</div>
            <p>{ticket.complaint_text || "No complaint text available."}</p>
            {ticket.routing_reason && <div className="td-routing-note"><FiCpu /><span><strong>AI routing reason:</strong> {ticket.routing_reason}</span></div>}
          </section>

          {/* =====================================================
                ASSIGNMENT / OWNERSHIP
                ===================================================== */}

            <div className="ticket-owner-card">
            <div className="ticket-owner-header">
                <span className="section-kicker">
                CURRENT OWNER
                </span>

                {ticket.assigned_agent_id ? (
                <span className="owner-status assigned">
                    ASSIGNED
                </span>
                ) : (
                <span className="owner-status unassigned">
                    UNASSIGNED
                </span>
                )}
            </div>

            {ticket.assigned_agent_id ? (
                <div className="ticket-owner-content">
                <div className="person-avatar">
                    {initials(
                    ticket.assigned_agent_name ||
                    "Resolver"
                    )}
                </div>

                <div className="ticket-owner-info">
                    <strong>
                    {ticket.assigned_agent_name ||
                        `Resolver #${ticket.assigned_agent_id}`}
                    </strong>

                    <span>
                    {ticket.assigned_team ||
                        "Operational Team"}
                    </span>

                    <small>
                    Resolver ID: #{ticket.assigned_agent_id}
                    </small>
                </div>
                </div>
            ) : (
                <div className="ticket-owner-content unassigned-owner">
                <div className="owner-unassigned-icon">
                    ?
                </div>

                <div className="ticket-owner-info">
                    <strong>
                    No resolver assigned
                    </strong>

                    <span>
                    {ticket.assigned_team ||
                        "No operational team"}
                    </span>

                    <small>
                    Manual assignment may be required
                    </small>
                </div>
                </div>
            )}
            {mode === "admin" && (
              <div className="td-action-row">
                {active && <button className="td-primary" disabled={loading} onClick={() => onAutoAssign(ticket.id)}><FiZap /> Auto assign best</button>}
                {ticket.status === "OPEN" && ticket.assigned_agent_id && <button className="td-secondary" disabled={loading} onClick={() => onStatus(ticket.id, "IN_PROGRESS")}><FiPlay /> Start work</button>}
                {ticket.status === "IN_PROGRESS" && <button className="td-secondary" disabled={loading} onClick={() => onStatus(ticket.id, "PENDING_CUSTOMER")}><FiPause /> Pending customer</button>}
                {ticket.status === "PENDING_CUSTOMER" && <button className="td-secondary" disabled={loading} onClick={() => onStatus(ticket.id, "IN_PROGRESS")}><FiPlay /> Resume</button>}
                {ticket.assigned_agent_id && active && <button className="td-success" disabled={loading} onClick={() => onStatus(ticket.id, "RESOLVED")}><FiCheckCircle /> Resolve</button>}
                {active && <button className="td-danger" disabled={loading} onClick={() => onEscalate(ticket.id)}><FiAlertTriangle /> Escalate</button>}
              </div>)}
            
            </div>

          {mode === "admin" && (
            <section className="td-card routing-card">
              <div className="td-section-heading"><div><div className="td-card-label"><FiZap /> ROUTING INTELLIGENCE</div><h3>Who should own this ticket?</h3></div><StateBadge tone="info">AI + WORKFORCE</StateBadge></div>

              {selected && (
                <div className="td-selected-agent">
                  <div className="td-person"><div className="td-avatar accent">{initials(selected.agent_name)}</div><div><span>Recommended resolver</span><strong>{selected.agent_name}</strong></div></div>
                  <div className={`td-score ${scoreTone(selected.score)}`}><strong>{Math.round(selected.score)}</strong><span>ROUTING SCORE</span></div>
                </div>
              )}

              

              <div className="td-candidate-list">
                {candidates.length ? candidates.map((candidate) => (
                  <div className="td-candidate" key={candidate.agent_id}>
                    <div className="td-candidate-main"><div className="td-avatar">{initials(candidate.agent_name)}</div><div><strong>{candidate.agent_name}</strong><span>AI score {Math.round(candidate.score)}</span></div></div>
                    <Metric label="Skill" value={candidate.skill_score} /><Metric label="Capacity" value={candidate.capacity_score} /><Metric label="Priority" value={candidate.priority_load_score} /><Metric label="Experience" value={candidate.experience_score} /><Metric label="SLA" value={candidate.sla_risk_score} />
                    <button className="td-outline" disabled={loading} onClick={() => onAssign(ticket.id, candidate.agent_id)}><FiUserCheck /> Assign</button>
                  </div>
                )) : <div className="td-empty"><FiAlertTriangle /><div><strong>{analysis?.message || "No automatic resolver is currently eligible."}</strong><span>Use the manual assignment control below to override workforce eligibility when operationally appropriate.</span></div></div>}
              </div>
            </section>
          )}

          {mode === "admin" && (
            <section className="td-card manual-card">
              <div className="td-section-heading"><div><div className="td-card-label"><FiUserCheck /> MANUAL CONTROL</div><h3>Assign directly to a resolver</h3></div><StateBadge tone="warning">ADMIN OVERRIDE</StateBadge></div>
              <p className="td-muted">Automatic routing respects workforce eligibility. Manual assignment lets operations intervene when a ticket must move immediately.</p>
              <div className="td-manual-grid">
                <select value={manualAgentId} onChange={(e) => { setManualAgentId(e.target.value); setManualConfirm(false); }} disabled={!manualAgents.length}>
                  <option value="">Select {operationalTeam} resolver</option>
                  {manualAgents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name} · {agent.open_tickets ?? 0}/{agent.max_concurrent_tickets ?? agent.capacity ?? "—"} · {agent.availability_status}</option>)}
                </select>
                <button className="td-primary" disabled={!selectedManualAgent || loading} onClick={assignManual}><FiUserCheck /> {manualConfirm ? "Confirm override" : "Assign resolver"}</button>
              </div>
              {selectedManualAgent && <div className={`td-override ${atCapacity ? "danger" : "safe"}`}><strong>{atCapacity ? "Capacity override required" : "Resolver is within capacity"}</strong><span>{selectedManualAgent.name}: {selectedManualAgent.open_tickets ?? 0} active / {selectedManualAgent.max_concurrent_tickets ?? selectedManualAgent.capacity ?? "—"} capacity. {atCapacity ? "Manual assignment will exceed normal capacity." : "No capacity override is required."}</span></div>}
              {!manualAgents.length && <div className="td-empty small"><FiUser /><span>No active resolver is currently mapped to {operationalTeam}.</span></div>}
            </section>
          )}

          {mode === "agent" && ticket.request_type === "WORKDAY_COST_CENTER_EIB" && (
            <section className="td-card eib-launch-card">
              <div className="td-section-heading">
                <div>
                  <div className="td-card-label"><FiZap /> WORKDAY EIB</div>
                  <h3>Cost Center EIB launch</h3>
                </div>
                <StateBadge tone="info">DIRECT LAUNCH</StateBadge>
              </div>
              <p className="td-muted">You can launch the uploaded Cost Center EIB template directly in Workday. The uploaded file is sent as-is; no mapping or transformation is performed.</p>
              <div className="td-action-row">
                <button className="td-primary" disabled={loading} onClick={() => onLaunchCostCenterEib?.(ticket.id)}><FiZap /> {loading ? "Launching..." : "Launch Cost Center EIB"}</button>
              </div>
            </section>
          )}

          {mode === "agent" && (
            <>
              <section className="td-card ai-resolution-card">
                <div className="td-section-heading">
                  <div>
                    <div className="td-card-label">
                      <FiCpu /> AI RESOLUTION ASSISTANT
                    </div>
                    <h3>Recommended next steps</h3>
                  </div>

                  <div className="ai-help-wrap">
                    <button
                      className="ai-help-button"
                      onClick={() => setShowAiHelp((value) => !value)}
                      aria-label="AI resolution help"
                      title="How AI resolution assistance works"
                    >
                      <FiHelpCircle />
                    </button>

                    {showAiHelp && (
                      <div className="ai-help-popover">
                        <strong>Resolution assistance</strong>
                        <p>
                          We can add a solution reccomendation based on your previous data.
                        </p>
                        <span>
                          For now, the assistant uses the current ticket and Groq to suggest a practical troubleshooting path.
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <p className="td-muted ai-disclaimer">
                  AI guidance is a recommendation. Verify each step against your team's procedures before making changes.
                </p>

                {!resolutionRecommendation ? (
                  <div className="ai-empty-state">
                    <div className="ai-empty-icon"><FiCpu /></div>
                    <div>
                      <strong>Generate a resolver recommendation</strong>
                      <span>
                        Get a diagnosis, investigation steps, verification checks and a suggested customer response.
                      </span>
                    </div>
                    <div className="ai-action-group">
                      <button
                        className="td-primary ai-generate-button"
                        onClick={() => onLoadResolutionRecommendation?.(ticket.id)}
                        disabled={aiLoading}
                      >
                        <FiZap />
                        {aiLoading ? "Generating..." : "Generate solution"}
                      </button>
                      <button
                        className="td-secondary ai-context-button"
                        onClick={() => {
                          if (!resolutionContext) onLoadResolutionContext?.(ticket.id);
                          setShowResolutionContext(true);
                        }}
                      >
                        <FiBookOpen /> View context
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="ai-resolution-content">
                    <div className="ai-confidence-row">
                      <span>AI confidence</span>
                      <strong>
                        {Math.round((resolutionRecommendation.confidence || 0) * 100)}%
                      </strong>
                    </div>

                    <div className="ai-diagnosis">
                      <span>DIAGNOSIS</span>
                      <strong>{resolutionRecommendation.summary || "No summary returned."}</strong>
                    </div>

                    <div className="ai-two-column">
                      <div>
                        <span className="ai-subheading">Likely root cause</span>
                        <p>{resolutionRecommendation.likely_root_cause || "No root-cause hypothesis returned."}</p>
                      </div>

                      <div>
                        <span className="ai-subheading">Caution</span>
                        <p>{resolutionRecommendation.caution || "Validate the result before closing the ticket."}</p>
                      </div>
                    </div>

                    <div className="ai-step-section">
                      <span className="ai-subheading">Recommended investigation</span>
                      <ol>
                        {(resolutionRecommendation.recommended_steps || []).map((step, index) => (
                          <li key={`${index}-${step}`}>{step}</li>
                        ))}
                      </ol>
                    </div>

                    <div className="ai-step-section">
                      <span className="ai-subheading">Verification</span>
                      <ul>
                        {(resolutionRecommendation.verification || []).map((step, index) => (
                          <li key={`${index}-${step}`}>{step}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="ai-customer-response">
                      <span className="ai-subheading">Suggested customer response</span>
                      <p>{resolutionRecommendation.customer_response || "No response draft returned."}</p>
                    </div>

                    <div className="ai-action-group ai-bottom-actions">
                      <button
                        className="td-secondary ai-context-button"
                        onClick={() => {
                          if (!resolutionContext) onLoadResolutionContext?.(ticket.id);
                          setShowResolutionContext(true);
                        }}
                      >
                        <FiBookOpen /> View context
                      </button>
                      <button
                        className="td-secondary ai-refresh ai-refresh-button"
                        onClick={() => onLoadResolutionRecommendation?.(ticket.id)}
                        disabled={aiLoading}
                      >
                        <FiRefreshCw />
                        {aiLoading ? "Refreshing..." : "Refresh recommendation"}
                      </button>
                    </div>
                  </div>
                )}
              </section>

              <section className="td-card similar-tickets-card">
                <div className="td-section-heading">
                  <div>
                    <div className="td-card-label">
                      <FiBookOpen /> SIMILAR RESOLVED TICKETS
                    </div>
                    <h3>Use previous successful cases as reference</h3>
                  </div>
                  <button
                    className="td-secondary similar-refresh-button"
                    onClick={() => onLoadSimilarTickets?.(ticket.id)}
                    disabled={similarLoading}
                  >
                    <FiRefreshCw />
                    {similarLoading ? "Searching..." : "Refresh"}
                  </button>
                </div>

                <p className="td-muted">
                  These are previously resolved or closed tickets that most closely match the current issue.
                </p>

                {similarLoading && (
                  <div className="similar-loading">Finding relevant historical cases...</div>
                )}

                {!similarLoading && similarTickets.length === 0 && (
                  <div className="td-empty">
                    <FiBookOpen />
                    <div>
                      <strong>No sufficiently similar resolved cases found.</strong>
                      <span>Resolve more tickets and this reference library will become more useful.</span>
                    </div>
                  </div>
                )}

                {!similarLoading && similarTickets.length > 0 && (
                  <div className="similar-ticket-list">
                    {similarTickets.map((item) => (
                      <article className="similar-ticket" key={item.ticket_id}>
                        <div className="similar-ticket-top">
                          <span className="similar-ticket-id">#{item.ticket_id}</span>
                          <StateBadge tone="info">
                            {Math.round((item.similarity_score || 0) * 100)}% similar
                          </StateBadge>
                          <StateBadge>{item.status}</StateBadge>
                        </div>

                        <h4>{item.summary || item.category || "Resolved support case"}</h4>

                        <p>{item.complaint_text || "No historical complaint text available."}</p>

                        <div className="similar-ticket-meta">
                          <span>{item.category || "—"}</span>
                          <span>{item.subcategory || "—"}</span>
                          <span>{item.priority_level || "—"}</span>
                          {item.assigned_agent_name && <span>Resolved by {item.assigned_agent_name}</span>}
                        </div>

                        {item.resolution_outcome && (
                          <div className="similar-ticket-outcome">
                            <strong>Recorded resolution context</strong>
                            <span>{item.resolution_outcome}</span>
                          </div>
                        )}
                      </article>
                    ))}
                  </div>
                )}
              </section>

              {showResolutionContext && (
                <div className="resolution-context-backdrop" onMouseDown={(event) => {
                  if (event.target === event.currentTarget) setShowResolutionContext(false);
                }}>
                  <div className="resolution-context-modal">
                    <div className="resolution-context-header">
                      <div>
                        <span className="section-kicker">RETRIEVED RESOLUTION CONTEXT</span>
                        <h3>Evidence used for this ticket</h3>
                        <p>Hybrid semantic + lexical retrieval with reciprocal-rank fusion and cross-encoder reranking.</p>
                      </div>
                      <button className="td-icon-button" onClick={() => setShowResolutionContext(false)}>×</button>
                    </div>

                    <div className="resolution-context-body">
                      {!resolutionContext && (
                        <div className="td-empty">
                          <FiRefreshCw />
                          <div><strong>Loading resolution context...</strong><span>Searching historical tickets, the controlled SOP and the knowledge base.</span></div>
                        </div>
                      )}

                      {resolutionContext && (
                        <>
                          <div className="resolution-context-meta">
                            <span>{resolutionContext.method}</span>
                            <span>Embedding: {resolutionContext.embedding_model}</span>
                            <span>Reranker: {resolutionContext.reranker_model}</span>
                          </div>

                          <div className="context-source-section">
                            <div className="context-source-heading">
                              <div><span className="section-kicker">TICKET DUMP</span><h4>Historical resolved cases</h4></div>
                              <span>{resolutionContext.tickets?.length || 0} retrieved</span>
                            </div>
                            <div className="context-card-list">
                              {(resolutionContext.tickets || []).map((item) => (
                                <article className="context-evidence-card" key={`${item.source_type}-${item.source_id}`}>
                                  <div className="context-evidence-top">
                                    <strong>Ticket #{item.ticket_id}</strong>
                                    <span>{item.status}</span>
                                    <span>{item.rerank_score != null ? `Reranker ${Number(item.rerank_score).toFixed(2)}` : "Hybrid match"}</span>
                                  </div>
                                  <h5>{item.title}</h5>
                                  <div className="context-chip-row">
                                    <span>{item.category || "—"}</span>
                                    <span>{item.subcategory || "—"}</span>
                                    <span>{item.priority_level || "—"}</span>
                                    {item.assigned_agent_name && <span>Resolved by {item.assigned_agent_name}</span>}
                                  </div>
                                  <p><strong>Complaint:</strong> {item.complaint_text || "Historical complaint text unavailable."}</p>
                                  <details><summary>View historical record</summary><pre>{item.content}</pre></details>
                                </article>
                              ))}
                            </div>
                          </div>

                          <div className="context-source-section">
                            <div className="context-source-heading">
                              <div><span className="section-kicker">CONTROLLED SOP</span><h4>Relevant procedure sections</h4></div>
                              <span>{resolutionContext.sop?.length || 0} retrieved</span>
                            </div>
                            <div className="context-card-list">
                              {(resolutionContext.sop || []).map((item) => (
                                <article className="context-evidence-card controlled" key={`${item.source_type}-${item.source_id}`}>
                                  <div className="context-evidence-top">
                                    <strong>{item.article_id || item.source_id}</strong>
                                    <span>{item.title}</span>
                                  </div>
                                  <details open><summary>View SOP section</summary><pre>{item.content}</pre></details>
                                </article>
                              ))}
                            </div>
                          </div>

                          <div className="context-source-section">
                            <div className="context-source-heading">
                              <div><span className="section-kicker">KNOWLEDGE BASE</span><h4>Relevant troubleshooting articles</h4></div>
                              <span>{resolutionContext.kb?.length || 0} retrieved</span>
                            </div>
                            <div className="context-card-list">
                              {(resolutionContext.kb || []).map((item) => (
                                <article className="context-evidence-card controlled" key={`${item.source_type}-${item.source_id}`}>
                                  <div className="context-evidence-top">
                                    <strong>{item.article_id || item.source_id}</strong>
                                    <span>{item.title}</span>
                                  </div>
                                  <details open><summary>View KB section</summary><pre>{item.content}</pre></details>
                                </article>
                              ))}
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <section className="td-card controls-card">
            <div className="td-section-heading"><div><div className="td-card-label">TICKET CONTROL</div><h3>Priority and lifecycle</h3></div></div>
            <div className="td-control-grid">
              <label>Priority<select value={ticket.priority_level || "Medium"} onChange={(e) => onPriority?.(ticket.id, e.target.value)}><option disabled>Select priority</option>{PRIORITIES.map((p) => <option key={p}>{p}</option>)}</select></label>
              <label>Status<select value={ticket.status} onChange={(e) => onStatus?.(ticket.id, e.target.value)} disabled={mode !== "admin" && !ticket.assigned_agent_id}>{STATUS_OPTIONS.map((s) => <option key={s}>{s}</option>)}</select></label>
            </div>
          </section>

          <section className="td-card timeline-card">
            <div className="td-section-heading"><div><div className="td-card-label"><FiClock /> AUDIT TRAIL</div><h3>Ticket history</h3></div><span className="td-muted">{events?.length || 0} events</span></div>
            <div className="td-timeline">
              {events?.length ? events.map((event) => (
                <div className="td-event" key={event.id}>
                  <div className="td-event-dot" />
                  <div><strong>{String(event.event_type || "EVENT").replaceAll("_", " ")}</strong><span>{event.from_value || event.to_value ? `${event.from_value || "—"} → ${event.to_value || "—"}` : "Operational event"}</span><small>{event.notes || ""}</small><time>{event.created_at || ""}</time></div>
                </div>
              )) : <div className="td-empty"><FiClock /><span>No events recorded.</span></div>}
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
