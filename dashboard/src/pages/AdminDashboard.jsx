/**
 * AdminDashboard.jsx — Full admin triage dashboard.
 *
 * Refactored from the original App.jsx monolith. Now:
 *   - Uses JWT auth via AuthContext (no legacy password modal)
 *   - Shows logged-in admin name in Navbar
 *   - Includes a "Pending Admin Approvals" section at the top
 *   - Retains all original functionality:
 *       Ward Accountability table, Simulate Intake (text + voice), complaint feed with triage dropdowns
 *
 * Authentication:
 *   For simulate/classify/transcribe calls, uses JWT Bearer token.
 *   For complaint status updates, uses JWT Bearer token.
 */

import React, { useState, useEffect } from "react";
import {
  Building2, AlertTriangle, Clock, RefreshCw, Layers,
  CheckCircle2, ShieldAlert, PlusCircle, Filter,
  FileText, Volume2, UserCheck, XCircle, ChevronDown
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/Navbar";
import "../App.css";

import { API_BASE } from "../config";

export default function AdminDashboard() {
  const { token } = useAuth();

  // ── Core data ──
  const [complaints, setComplaints] = useState([]);
  const [wards, setWards] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  // ── Pending admin approvals ──
  const [pendingAdmins, setPendingAdmins] = useState([]);
  const [approvingId, setApprovingId] = useState(null);

  // ── Filters ──
  const [filterWard, setFilterWard] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // ── Simulation form ──
  const [rawInput, setRawInput] = useState("");
  const [formWardId, setFormWardId] = useState("");
  const [locationDescription, setLocationDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [simResult, setSimResult] = useState(null);

  // ── Voice intake ──
  const [intakeMode, setIntakeMode] = useState("text");
  const [audioFile, setAudioFile] = useState(null);
  const [transcribing, setTranscribing] = useState(false);
  const [originalTranscript, setOriginalTranscript] = useState("");
  const [detectedLanguage, setDetectedLanguage] = useState("English");
  const [transcriptionSuccess, setTranscriptionSuccess] = useState(true);

  // ── Auth headers (JWT) ──
  const jwtHeaders = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // ── Data fetch ──
  const fetchData = async () => {
    try {
      setLoading(true);
      const [wardsRes, deptsRes, complaintsRes] = await Promise.all([
        fetch(`${API_BASE}/wards`),
        fetch(`${API_BASE}/departments`),
        fetch(`${API_BASE}/complaints`),
      ]);
      if (wardsRes.ok && deptsRes.ok && complaintsRes.ok) {
        const wardsData = await wardsRes.json();
        const deptsData = await deptsRes.json();
        const complaintsData = await complaintsRes.json();
        setWards(wardsData);
        setDepartments(deptsData);
        setComplaints(complaintsData);
        setConnected(true);
      } else {
        setConnected(false);
      }
    } catch (err) {
      console.error("API Connection failure:", err);
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingAdmins = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/admin/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setPendingAdmins(await res.json());
    } catch { /* silently ignore */ }
  };

  useEffect(() => {
    fetchData();
    fetchPendingAdmins();
  }, []);

  useEffect(() => {
    if (wards.length > 0 && !formWardId) {
      setFormWardId(wards[0].id.toString());
    }
  }, [wards]);

  // ── Approve / Reject pending admin ──
  const handleApproveAdmin = async (userId, action, reason = null) => {
    setApprovingId(userId);
    try {
      const res = await fetch(`${API_BASE}/auth/admin/approve/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action, rejection_reason: reason }),
      });
      if (res.ok) {
        await fetchPendingAdmins();
      } else {
        const err = await res.json();
        alert(`Action failed: ${err.detail}`);
      }
    } catch { alert("Network error during admin approval."); }
    finally { setApprovingId(null); }
  };

  // ── Status update ──
  const handleStatusChange = async (complaintId, newStatus) => {
    try {
      const response = await fetch(`${API_BASE}/complaints/${complaintId}/status`, {
        method: "PATCH",
        headers: jwtHeaders,
        body: JSON.stringify({
          status: newStatus,
          notes: `Status changed to ${newStatus} via Administrator Dashboard.`,
        }),
      });
      if (response.ok) await fetchData();
      else alert("Failed to update status.");
    } catch (err) {
      console.error("Failed to patch status:", err);
    }
  };

  // ── Audio transcription ──
  const handleTranscribeFile = async (fileToTranscribe) => {
    if (!fileToTranscribe) return;
    setTranscribing(true);
    setOriginalTranscript("");
    setRawInput("");
    setTranscriptionSuccess(true);
    const formData = new FormData();
    formData.append("file", fileToTranscribe);
    try {
      const response = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) throw new Error("Transcription API failed.");
      const data = await response.json();
      setRawInput(data.english_translation || "");
      setOriginalTranscript(data.original_transcription || "");
      setDetectedLanguage(data.originalLanguage || "English");
      setTranscriptionSuccess(data.transcription_success ?? true);
    } catch (err) {
      console.error("Transcription error:", err);
      setRawInput("Fallback: Audio transcription failed. Queued for manual triage.");
      setOriginalTranscript("");
      setDetectedLanguage("Unknown");
      setTranscriptionSuccess(false);
    } finally {
      setTranscribing(false);
    }
  };

  const loadSyntheticTestClip = async (filename) => {
    setTranscribing(true);
    setAudioFile(null);
    try {
      const response = await fetch(`${API_BASE}/test_audio/${filename}`);
      if (!response.ok) throw new Error(`Failed to load test clip: ${filename}`);
      const blob = await response.blob();
      const file = new File([blob], filename, { type: "audio/mpeg" });
      setAudioFile(file);
      await handleTranscribeFile(file);
    } catch (err) {
      console.error("Failed to load simulated ticket:", err);
      alert(`Simulation Error: ${err.message}`);
      setTranscribing(false);
    }
  };

  // ── Simulate intake ──
  const handleSimulateSubmit = async (e) => {
    e.preventDefault();
    if (!rawInput.trim() || !formWardId) return;
    setSubmitting(true);
    setSimResult(null);
    try {
      const classifyRes = await fetch(`${API_BASE}/classify`, {
        method: "POST",
        headers: jwtHeaders,
        body: JSON.stringify({
          raw_input: rawInput,
          ward_id: parseInt(formWardId),
          transcription_success: transcriptionSuccess,
          originalLanguage: detectedLanguage,
        }),
      });
      if (!classifyRes.ok) throw new Error("Classification step failed.");
      const classification = await classifyRes.json();

      const persistRes = await fetch(`${API_BASE}/complaints`, {
        method: "POST",
        headers: jwtHeaders,
        body: JSON.stringify({
          raw_input: rawInput,
          original_transcription: originalTranscript || null,
          originalLanguage: classification.originalLanguage || detectedLanguage,
          complaintType: classification.complaintType,
          translatedText: classification.translatedText || rawInput,
          mediaAttachments: [],
          urgency_score: classification.urgency_score,
          classification_method: classification.classification_method,
          location_description: locationDescription || "Simulated intake portal",
          ward_id: parseInt(formWardId),
          department_id: classification.department_id,
          transcription_success: transcriptionSuccess,
        }),
      });
      if (!persistRes.ok) throw new Error("Complaint persistence step failed.");

      setSimResult({
        category: classification.complaintType,
        urgency: classification.urgency_score,
        method: classification.classification_method,
        reasoning: classification.reasoning,
      });
      setRawInput("");
      setLocationDescription("");
      setAudioFile(null);
      setOriginalTranscript("");
      setDetectedLanguage("English");
      setTranscriptionSuccess(true);
      await fetchData();
    } catch (err) {
      console.error(err);
      alert(`Simulation Error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  // ── Metrics ──
  const getWardMetrics = () =>
    wards.map(ward => {
      const wardComplaints = complaints.filter(c => c.ward_id === ward.id);
      const resolved = wardComplaints.filter(c => c.status === "resolved" && c.resolution_time_seconds !== null);
      let avgTimeDescription = "N/A";
      if (resolved.length > 0) {
        const avgSecs = Math.round(resolved.reduce((acc, c) => acc + c.resolution_time_seconds, 0) / resolved.length);
        if (avgSecs < 60) avgTimeDescription = `${avgSecs}s`;
        else if (avgSecs < 3600) avgTimeDescription = `${Math.round(avgSecs / 60)}m`;
        else avgTimeDescription = `${Math.round(avgSecs / 3600)}h`;
      }
      return {
        id: ward.id,
        name: ward.name.replace("Ward ", "W"),
        total: wardComplaints.length,
        resolved: resolved.length,
        avgTime: avgTimeDescription,
      };
    });

  const totalCount = complaints.length;
  const avgUrgency = totalCount > 0
    ? (complaints.reduce((acc, c) => acc + (c.urgency_score || 0), 0) / totalCount).toFixed(1)
    : "0.0";
  const totalResolved = complaints.filter(c => c.status === "resolved").length;
  const resolutionRate = totalCount > 0 ? Math.round((totalResolved / totalCount) * 100) : 0;
  const llmRatio = totalCount > 0
    ? Math.round((complaints.filter(c => c.classification_method === "llm").length / totalCount) * 100)
    : 0;

  const filteredComplaints = complaints.filter(c => {
    const matchWard = filterWard === "" || c.ward_id === parseInt(filterWard);
    const matchStatus = filterStatus === "" || c.status === filterStatus;
    return matchWard && matchStatus;
  });

  return (
    <div className="page-wrapper">
      <Navbar />

      <div className="dashboard-container">

        {/* ── Pending Admin Approvals (if any) ── */}
        {pendingAdmins.length > 0 && (
          <section className="pending-admins-banner">
            <div className="pending-admins-header">
              <UserCheck size={18} />
              <h3>{pendingAdmins.length} Pending Admin Application{pendingAdmins.length > 1 ? "s" : ""}</h3>
            </div>
            <div className="pending-admins-list">
              {pendingAdmins.map(a => (
                <div className="pending-admin-card card" key={a.id}>
                  <div className="pending-admin-info">
                    <strong>{a.full_name}</strong>
                    <span>{a.email}</span>
                    <span>{a.phone || "—"}</span>
                    <span>Applied: {new Date(a.created_at).toLocaleDateString()}</span>
                    {a.admin_doc_filename && (
                      <a
                        href={`${API_BASE}/uploads/${a.admin_doc_filename}`}
                        target="_blank"
                        rel="noreferrer"
                        className="doc-link"
                      >
                        📄 View Document
                      </a>
                    )}
                  </div>
                  <div className="pending-admin-actions">
                    <button
                      className="btn btn-success btn-sm"
                      disabled={approvingId === a.id}
                      onClick={() => handleApproveAdmin(a.id, "approve")}
                    >
                      <UserCheck size={14} /> Approve
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      disabled={approvingId === a.id}
                      onClick={() => {
                        const reason = window.prompt("Enter rejection reason (optional):");
                        handleApproveAdmin(a.id, "reject", reason || null);
                      }}
                    >
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Header ── */}
        <header className="header">
          <div className="header-title-group">
            <h1>Triage Dashboard</h1>
            <p>SDG 11 Accountability &amp; Complaint Management</p>
          </div>
          <div className="header-controls">
            <div className={`connection-pill ${connected ? "connected" : "disconnected"}`}>
              <span className="pulsing-dot" />
              <span>{connected ? "LIVE BACKEND LINKED" : "CONNECTION OFFLINE"}</span>
            </div>
          </div>
        </header>

        {/* ── Stats Grid ── */}
        <section className="stats-grid">
          <div className="card stat-card">
            <div className="stat-icon"><Layers size={24} /></div>
            <div className="stat-details">
              <h3>Total Registered</h3>
              <p>{totalCount} complaints</p>
            </div>
          </div>
          <div className="card stat-card">
            <div className="stat-icon"><AlertTriangle size={24} /></div>
            <div className="stat-details">
              <h3>Avg Urgency</h3>
              <p className="glow-text-primary">{avgUrgency} / 5</p>
            </div>
          </div>
          <div className="card stat-card">
            <div className="stat-icon"><CheckCircle2 size={24} /></div>
            <div className="stat-details">
              <h3>Resolution Rate</h3>
              <p>{resolutionRate}% ({totalResolved} closed)</p>
            </div>
          </div>
          <div className="card stat-card">
            <div className="stat-icon"><ShieldAlert size={24} /></div>
            <div className="stat-details">
              <h3>LLM Routing Ratio</h3>
              <p>{llmRatio}% dynamic AI</p>
            </div>
          </div>
        </section>

        {/* ── Main Grid ── */}
        <div className="main-grid">
          {/* Sidebar */}
          <aside className="sidebar">

            {/* Ward Accountability */}
            <div className="card">
              <h2><Clock size={18} /> Ward Accountability</h2>
              <p style={{ color: "var(--text-secondary)", fontSize: "12px", marginBottom: "16px" }}>
                Average response times calculated against resolved cases.
              </p>
              <table className="metrics-table">
                <thead>
                  <tr>
                    <th>Ward</th>
                    <th style={{ textAlign: "center" }}>Total</th>
                    <th style={{ textAlign: "center" }}>Resolved</th>
                    <th style={{ textAlign: "right" }}>Avg Time</th>
                  </tr>
                </thead>
                <tbody>
                  {getWardMetrics().map(metric => (
                    <tr key={metric.id}>
                      <td>{metric.name}</td>
                      <td style={{ textAlign: "center" }}>{metric.total}</td>
                      <td style={{ textAlign: "center" }}>{metric.resolved}</td>
                      <td className="bold-value" style={{ textAlign: "right" }}>{metric.avgTime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Simulate Intake (Admin Only) */}
            <div className="card">
              <h2><PlusCircle size={18} /> Simulate Citizen Intake</h2>

              {/* Tabs */}
              <div className="intake-tabs">
                <button
                  type="button"
                  className={`intake-tab-btn ${intakeMode === "text" ? "active" : ""}`}
                  onClick={() => { setIntakeMode("text"); setRawInput(""); setOriginalTranscript(""); setDetectedLanguage("English"); setTranscriptionSuccess(true); setAudioFile(null); }}
                >
                  <FileText size={14} /> Text Intake
                </button>
                <button
                  type="button"
                  className={`intake-tab-btn ${intakeMode === "voice" ? "active" : ""}`}
                  onClick={() => { setIntakeMode("voice"); setRawInput(""); setOriginalTranscript(""); setDetectedLanguage("Unknown"); setTranscriptionSuccess(true); setAudioFile(null); }}
                >
                  <Volume2 size={14} /> Voice Note Upload
                </button>
              </div>

              <form className="intake-form" onSubmit={handleSimulateSubmit}>
                {intakeMode === "text" ? (
                  <div className="form-group">
                    <label>Raw citizen complaint text:</label>
                    <textarea
                      rows="3"
                      placeholder="Describe electrical, water, sanitation or road issues…"
                      value={rawInput}
                      onChange={e => setRawInput(e.target.value)}
                      required
                    />
                  </div>
                ) : (
                  <div className="form-group" style={{ gap: "10px" }}>
                    <label>Upload Citizen Audio File (.mp3, .wav):</label>
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={e => { const file = e.target.files[0]; setAudioFile(file); handleTranscribeFile(file); }}
                      style={{ fontSize: "12px", border: "1.5px dashed var(--border-color)", padding: "12px", background: "#FFFFFF", borderRadius: "8px", color: "var(--text-secondary)" }}
                    />
                    <div className="audio-quick-test">
                      <p>Or select synthetic clean audio test clip:</p>
                      <div className="audio-btn-grid">
                        <button type="button" className="audio-test-btn" onClick={() => loadSyntheticTestClip("hi_complaint.mp3")} disabled={transcribing}>🗣️ Hindi (Waste)</button>
                        <button type="button" className="audio-test-btn" onClick={() => loadSyntheticTestClip("mr_complaint.mp3")} disabled={transcribing}>🗣️ Marathi (Power)</button>
                        <button type="button" className="audio-test-btn" onClick={() => loadSyntheticTestClip("kn_complaint.mp3")} disabled={transcribing}>🗣️ Kannada (Water)</button>
                        <button type="button" className="audio-test-btn danger-btn" onClick={() => { setTranscribing(true); setTimeout(() => { setRawInput("Fallback: Audio transcription failed. Queued for manual triage."); setOriginalTranscript(""); setDetectedLanguage("Unknown"); setTranscriptionSuccess(false); setTranscribing(false); }, 1000); }} disabled={transcribing}>⚠️ Corrupt (Fallback)</button>
                      </div>
                    </div>
                    {transcribing && (
                      <div className="transcribing-indicator">
                        <RefreshCw size={14} className="spinner-icon" />
                        <span>Transcribing &amp; Translating Audio via Gemini…</span>
                      </div>
                    )}
                    {rawInput && !transcribing && (
                      <div className="original-info-panel">
                        <div className="original-info-title">
                          Detected Language: {detectedLanguage} {transcriptionSuccess ? "✓" : "(Triage Fallback)"}
                        </div>
                        {originalTranscript && <p className="original-info-content" style={{ marginBottom: "6px" }}><strong>Original Voice Text:</strong> "{originalTranscript}"</p>}
                        <p className="original-info-content"><strong>English Translation:</strong> "{rawInput}"</p>
                      </div>
                    )}
                  </div>
                )}

                <div className="form-group">
                  <label>Administrative Ward Location:</label>
                  <select value={formWardId} onChange={e => setFormWardId(e.target.value)} required>
                    <option value="">Select Ward Region…</option>
                    {wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Specific Location Landmark:</label>
                  <input type="text" placeholder="e.g. Near main bus-stand, flat 4B" value={locationDescription} onChange={e => setLocationDescription(e.target.value)} />
                </div>

                <button type="submit" className="submit-btn" disabled={submitting || transcribing || !rawInput}>
                  {submitting ? (
                    <><RefreshCw size={16} className="pulse-indicator" /><span>CLASSIFYING COMPLAINT…</span></>
                  ) : (
                    <span>SUBMIT SIMULATED WEBHOOK</span>
                  )}
                </button>
              </form>

              {simResult && (
                <div style={{ marginTop: "16px", padding: "12px", background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: "8px", fontSize: "13px" }}>
                  <p style={{ fontWeight: 600, color: "var(--color-primary)" }}>AI Classification Result:</p>
                  <p style={{ marginTop: "4px" }}><strong>Category:</strong> {simResult.category}</p>
                  <p><strong>Urgency:</strong> {simResult.urgency}/5</p>
                  <p><strong>Method Used:</strong> {simResult.method}</p>
                  <p style={{ marginTop: "4px", fontStyle: "italic", fontSize: "12px", color: "var(--text-secondary)" }}>{simResult.reasoning}</p>
                </div>
              )}
            </div>
          </aside>

          {/* Main: Complaint Feed */}
          <main style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Filters */}
            <div className="card filters-bar">
              <h2 style={{ fontSize: "16px", display: "flex", alignItems: "center", gap: "6px", margin: 0 }}>
                <Filter size={16} /> Filters
              </h2>
              <div className="filter-dropdowns">
                <select className="filter-select" value={filterWard} onChange={e => setFilterWard(e.target.value)}>
                  <option value="">All Wards</option>
                  {wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
                <select className="filter-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="manual_review">Manual Review</option>
                  <option value="routed">Routed</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
                {(filterWard || filterStatus) && (
                  <button className="clear-btn" onClick={() => { setFilterWard(""); setFilterStatus(""); }}>Clear Filters</button>
                )}
              </div>
            </div>

            {/* Complaints List */}
            <div className="ticket-list">
              {filteredComplaints.length === 0 ? (
                <div className="card empty-tickets">
                  <Layers size={40} className="pulse-indicator" />
                  <p>No complaints matched your search filter criteria.</p>
                </div>
              ) : (
                filteredComplaints.map(complaint => {
                  const urgencyClass =
                    complaint.urgency_score >= 4 ? "badge-urgency-high" :
                    complaint.urgency_score >= 3 ? "badge-urgency-mid" :
                    "badge-urgency-low";
                  const methodClass = complaint.classification_method === "llm" ? "badge-method-llm" : "badge-method-fallback";
                  return (
                    <div className={`card ticket-card ${complaint.status === "manual_review" ? "ticket-card-warning" : ""}`} key={complaint.id}>
                      <div className="ticket-header">
                        <p className="ticket-title">"{complaint.raw_input}"</p>
                        <div className="badge-group">
                          <span className="badge badge-category">{complaint.complaintType}</span>
                          <span className={`badge ${urgencyClass}`}>Urgency {complaint.urgency_score}/5</span>
                          {complaint.originalLanguage && (
                            <span className="badge badge-language">
                              {complaint.originalLanguage === "Unknown" ? "Unidentified" : `Originally ${complaint.originalLanguage}`}
                            </span>
                          )}
                          <span className={`badge ${methodClass}`}>{complaint.classification_method}</span>
                          {complaint.status === "manual_review" && <span className="badge badge-status-manual">Awaiting Triage</span>}
                        </div>
                      </div>
                      <div className="ticket-meta">
                        <div className="meta-item"><span className="meta-label">Assigned Department</span>{complaint.department_name || "Unassigned"}</div>
                        <div className="meta-item"><span className="meta-label">Location Landmark</span>{complaint.location_description || "N/A"}</div>
                        <div className="meta-item"><span className="meta-label">Ward Region</span>{complaint.ward_name || `Ward ${complaint.ward_id}`}</div>
                        <div className="meta-item"><span className="meta-label">Registered Timestamp</span>{new Date(complaint.timestamp).toLocaleString()}</div>
                      </div>
                      {complaint.portal_name && (
                        <div className={`ticket-portal-dispatch ${complaint.portal_status === "Inferred" ? "portal-inferred" : "portal-verified"}`}>
                          <span className="portal-label">External Dispatch Target:</span>
                          <a
                            href={complaint.portal_url}
                            target="_blank"
                            rel="noreferrer"
                            className="portal-link"
                          >
                            {complaint.portal_status === "Inferred" ? "⚠️ " : "🔗 "}
                            {complaint.portal_name}
                          </a>
                          {complaint.portal_status === "Inferred" ? (
                            <div className="portal-disclaimer-text">
                              <strong>Disclaimer:</strong> {complaint.portal_citation || "Inferred fallback portal; not directly verified."}
                            </div>
                          ) : (
                            <div className="portal-verified-text">
                              <strong>Verified Link:</strong> Direct official portal citation.
                            </div>
                          )}
                          <div className="portal-general-guidance">
                            Note: Portal details are provided as a guide and may change; please confirm on the official site before filing.
                          </div>
                        </div>
                      )}
                      {complaint.original_transcription && (
                        <div className="ticket-original-text"><strong>Native Audio Text:</strong> "{complaint.original_transcription}"</div>
                      )}
                      <div className="ticket-actions">
                        <div className="time-metric">
                          {complaint.status === "resolved" ? (
                            <span style={{ color: "var(--color-success)" }}>Resolved in {complaint.resolution_time_seconds ? `${complaint.resolution_time_seconds}s` : "N/A"}</span>
                          ) : (
                            <span>Active ticket — awaiting dispatch</span>
                          )}
                        </div>
                        <div className="status-triage">
                          <span>Triage Status:</span>
                          {/* Admin always sees the editable dropdown */}
                          <select
                            className="status-select"
                            value={complaint.status}
                            onChange={e => handleStatusChange(complaint.id, e.target.value)}
                          >
                            <option value="pending">Pending</option>
                            <option value="manual_review">Manual Review</option>
                            <option value="routed">Routed</option>
                            <option value="in_progress">In Progress</option>
                            <option value="resolved">Resolved</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
