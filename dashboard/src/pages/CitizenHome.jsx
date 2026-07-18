/**
 * CitizenHome.jsx — Home page for authenticated citizens.
 *
 * Shows:
 *   - Greeting banner with user name and ward
 *   - Ward stats: active complaints, % resolved
 *   - Complaint feed (ward-filtered, read-only status badges)
 *   - Floating "+ Report an Issue" button → opens AddComplaint modal
 *
 * All complaints shown are from the citizen's ward (GET /complaints/my),
 * so they see the full accountability picture — not just their own filings.
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/Navbar";
import AddComplaint from "./AddComplaint";
import {
  Layers, CheckCircle2, AlertTriangle, Clock, Plus,
  RefreshCw, MapPin, Filter
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

// Human-readable status labels
const STATUS_LABELS = {
  pending: "Pending",
  in_progress: "In Progress",
  manual_review: "Manual Review",
  routed: "Routed",
  resolved: "Resolved",
};
const STATUS_COLORS = {
  pending: "#EF6C00",
  in_progress: "#1565C0",
  manual_review: "#C62828",
  routed: "#5C6BC0",
  resolved: "#2E7D32",
};

const COMPLAINT_TYPES = [
  "Water", "Sanitation", "Electricity", "Roads", "Public Safety", "Other"
];

const ORIGINAL_LANGUAGES = [
  "English", "Hindi", "Kannada", "Tamil", "Telugu", "Bengali", 
  "Marathi", "Gujarati", "Urdu", "Malayalam", "Punjabi", "Odia", "Unknown"
];

export default function CitizenHome() {
  const { token, user } = useAuth();
  const [complaints, setComplaints] = useState([]);
  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterLanguage, setFilterLanguage] = useState("");
  const [wardScope, setWardScope] = useState("my");
  const [stats, setStats] = useState({ total: 0, active: 0, resolved: 0, resolution_pct: 0 });
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [lightboxMedia, setLightboxMedia] = useState(null);

  // Automatically reset to Page 1 when any filter, scope, or page size changes
  useEffect(() => {
    setCurrentPage(1);
  }, [wardScope, filterStatus, filterType, filterLanguage, pageSize]);

  const wardObj = wards.find(w => w.id === user?.ward_id);

  const fetchComplaintsAndStats = async (scope = wardScope) => {
    setLoading(true);
    setComplaints([]);
    try {
      // 1. Fetch Wards list if empty
      let currentWards = wards;
      if (wards.length === 0) {
        const wardRes = await fetch(`${API_BASE}/wards`);
        if (wardRes.ok) {
          currentWards = await wardRes.json();
          setWards(currentWards);
        }
      }

      // 2. Resolve URIs based on selected scope
      let complaintsUrl = `${API_BASE}/complaints/my`;
      let statsUrl = `${API_BASE}/complaints/stats?scope=my`;
      const headers = { Authorization: `Bearer ${token}` };

      if (scope === "all") {
        complaintsUrl = `${API_BASE}/complaints`;
        statsUrl = `${API_BASE}/complaints/stats?scope=all`;
      } else if (scope !== "my") {
        complaintsUrl = `${API_BASE}/complaints?ward_id=${scope}`;
        statsUrl = `${API_BASE}/complaints/stats?scope=specific&ward_id=${scope}`;
      }

      // 3. Fetch complaints feed and banner stats aggregate in parallel
      const [complaintsRes, statsRes] = await Promise.all([
        fetch(complaintsUrl, { headers }),
        fetch(statsUrl, { headers }),
      ]);

      if (complaintsRes.ok) {
        setComplaints(await complaintsRes.json());
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaintsAndStats(wardScope);
  }, [wardScope]);

  // Combined feed filtering (AND logic)
  const filtered = complaints.filter(c => {
    if (filterStatus && c.status !== filterStatus) return false;
    if (filterType && c.complaintType !== filterType) return false;
    if (filterLanguage && c.originalLanguage !== filterLanguage) return false;
    return true;
  });

  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const paginatedItems = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="page-wrapper">
      <Navbar />

      <div className="citizen-page">
        {/* ── Greeting Banner ── */}
        <div className="citizen-hero">
          <div className="citizen-hero-text">
            <h1>Welcome back, {user?.full_name?.split(" ")[0] || "Citizen"} 👋</h1>
            <div className="ward-scope-selector" style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "8px", flexWrap: "wrap" }}>
              <span className="citizen-ward-badge" style={{ margin: 0 }}>
                <MapPin size={14} />
                {wardObj?.name || `Ward #${user?.ward_id}`}
              </span>
              <select
                className="filter-select"
                value={wardScope}
                onChange={e => setWardScope(e.target.value)}
                style={{
                  background: "rgba(255, 255, 255, 0.15)",
                  border: "1px solid rgba(255, 255, 255, 0.25)",
                  color: "#fff",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  outline: "none",
                  cursor: "pointer",
                  fontWeight: 500,
                  height: "28px"
                }}
              >
                <option value="my" style={{ color: "#333" }}>My Ward</option>
                <option value="all" style={{ color: "#333" }}>All Wards</option>
                {wards.map(w => (
                  <option key={w.id} value={w.id} style={{ color: "#333" }}>
                    {w.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {/* Stats chips */}
          <div className="citizen-hero-stats">
            <div className="citizen-stat-chip">
              <Layers size={16} />
              <span><strong>{stats.total}</strong> total</span>
            </div>
            <div className="citizen-stat-chip active">
              <AlertTriangle size={16} />
              <span><strong>{stats.active}</strong> active</span>
            </div>
            <div className="citizen-stat-chip resolved">
              <CheckCircle2 size={16} />
              <span><strong>{stats.resolution_pct}%</strong> resolved</span>
            </div>
          </div>
        </div>

        {/* ── Feed Header ── */}
        <div className="citizen-feed-header">
          <h2>
            <Clock size={18} /> Ward Complaint Feed
          </h2>
          <div className="filter-dropdowns">
            <select
              className="filter-select"
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="manual_review">Manual Review</option>
              <option value="routed">Routed</option>
              <option value="resolved">Resolved</option>
            </select>
            <select
              className="filter-select"
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
              title="Filter by Type"
            >
              <option value="">All Types</option>
              {COMPLAINT_TYPES.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <select
              className="filter-select"
              value={filterLanguage}
              onChange={e => setFilterLanguage(e.target.value)}
              title="Filter by Language"
            >
              <option value="">All Languages</option>
              {ORIGINAL_LANGUAGES.map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <select
              className="filter-select"
              value={pageSize}
              onChange={e => setPageSize(parseInt(e.target.value))}
              title="Page Size"
            >
              <option value={5}>5 per page</option>
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
              <option value={50}>50 per page</option>
            </select>
            {(filterStatus || filterType || filterLanguage) && (
              <button
                className="clear-btn"
                onClick={() => {
                  setFilterStatus("");
                  setFilterType("");
                  setFilterLanguage("");
                }}
              >
                Clear
              </button>
            )}
            <button className="btn btn-outline btn-sm" onClick={() => fetchComplaintsAndStats(wardScope)} title="Refresh">
              <RefreshCw size={14} className={loading ? "spinner-icon" : ""} />
            </button>
          </div>
        </div>

        {/* ── CSS Animations for skeleton loaders ── */}
        <style>{`
          @keyframes skeleton-pulse {
            0% { background-color: rgba(255, 255, 255, 0.04); }
            50% { background-color: rgba(255, 255, 255, 0.12); }
            100% { background-color: rgba(255, 255, 255, 0.04); }
          }
          .skeleton-card {
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            background: rgba(0, 0, 0, 0.01);
            display: flex;
            flex-direction: column;
            gap: 12px;
          }
          .skeleton-line {
            height: 12px;
            border-radius: 4px;
            background: rgba(0, 0, 0, 0.04);
            animation: skeleton-pulse 1.5s infinite ease-in-out;
          }
        `}</style>

        {/* ── Complaint Cards ── */}
        {loading && !complaints.length ? (
          <div className="ticket-list">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="skeleton-line" style={{ width: "65%", height: "16px" }}></div>
                  <div className="skeleton-line" style={{ width: "15%", height: "16px" }}></div>
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <div className="skeleton-line" style={{ width: "70px", height: "18px", borderRadius: "12px" }}></div>
                  <div className="skeleton-line" style={{ width: "50px", height: "18px", borderRadius: "12px" }}></div>
                  <div className="skeleton-line" style={{ width: "80px", height: "18px", borderRadius: "12px" }}></div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px", borderTop: "1px solid rgba(0,0,0,0.05)", paddingTop: "12px" }}>
                  <div className="skeleton-line" style={{ width: "35%", height: "12px" }}></div>
                  <div className="skeleton-line" style={{ width: "20%", height: "24px", borderRadius: "12px" }}></div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="card empty-tickets" style={{ textAlign: "center", padding: "48px 24px" }}>
            <Layers size={40} style={{ opacity: 0.3, margin: "0 auto 12px" }} />
            {complaints.length === 0 ? (
              <>
                <p>No complaints filed in this ward yet.</p>
                <button className="btn btn-primary" style={{ marginTop: "16px" }} onClick={() => setShowModal(true)}>
                  <Plus size={16} /> Be the first to report an issue
                </button>
              </>
            ) : (
              <>
                <p>No complaints match these combined filters.</p>
                <button
                  className="btn btn-outline"
                  style={{ marginTop: "16px" }}
                  onClick={() => {
                    setFilterStatus("");
                    setFilterType("");
                    setFilterLanguage("");
                  }}
                >
                  Reset All Filters
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="ticket-list">
            {paginatedItems.map(c => {
              const urgencyClass =
                c.urgency_score >= 4 ? "badge-urgency-high" :
                c.urgency_score >= 3 ? "badge-urgency-mid" : "badge-urgency-low";
              const statusColor = STATUS_COLORS[c.status] || "#666";

              return (
                <div
                  key={c.id}
                  className={`card ticket-card ${c.status === "manual_review" ? "ticket-card-warning" : ""}`}
                >
                  <div className="ticket-header">
                    <p className="ticket-title">"{c.raw_input}"</p>
                    <div className="badge-group">
                      {c.complaintType && <span className="badge badge-category">{c.complaintType}</span>}
                      {c.urgency_score && <span className={`badge ${urgencyClass}`}>Urgency {c.urgency_score}/5</span>}
                      {c.originalLanguage && (
                        <span className="badge badge-language">
                          {c.originalLanguage === "Unknown" ? "Unidentified" : `${c.originalLanguage}`}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="ticket-meta">
                    <div className="meta-item">
                      <span className="meta-label">Department</span>
                      {c.department_name || "Unassigned"}
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Location</span>
                      {c.location_description || "N/A"}
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Filed</span>
                      {new Date(c.timestamp).toLocaleString()}
                    </div>
                  </div>

                  {c.mediaAttachments && c.mediaAttachments.length > 0 && (
                    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px", padding: "0 16px 12px 16px" }}>
                      {c.mediaAttachments.map((att, i) => (
                        <div
                          key={i}
                          onClick={() => setLightboxMedia(att)}
                          style={{
                            width: "48px",
                            height: "48px",
                            borderRadius: "4px",
                            overflow: "hidden",
                            background: "#000",
                            cursor: "pointer",
                            border: "1px solid rgba(0,0,0,0.1)",
                            position: "relative"
                          }}
                        >
                          {att.type === "image" ? (
                            <img
                              src={att.url}
                              alt="attachment thumbnail"
                              style={{ width: "100%", height: "100%", objectFit: "cover" }}
                            />
                          ) : (
                            <div style={{ width: "100%", height: "100%", position: "relative" }}>
                              <video
                                src={att.url}
                                style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                preload="metadata"
                              />
                              <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.3)" }}>
                                <span style={{ color: "#fff", fontSize: "12px" }}>▶️</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="ticket-actions">
                    <div className="time-metric">
                      {c.status === "resolved"
                        ? <span style={{ color: "var(--color-success)" }}>
                            ✓ Resolved in {c.resolution_time_seconds ? `${c.resolution_time_seconds}s` : "N/A"}
                          </span>
                        : <span style={{ color: "var(--text-muted)" }}>Active — awaiting dispatch</span>}
                    </div>
                    {/* Read-only status badge (no dropdown for citizens) */}
                    <span
                      className="status-display"
                      style={{
                        background: `${statusColor}18`,
                        color: statusColor,
                        border: `1px solid ${statusColor}44`,
                        borderRadius: "20px",
                        padding: "4px 12px",
                        fontSize: "12px",
                        fontWeight: 600,
                      }}
                    >
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {/* ── Pagination Controls ── */}
        {totalPages > 1 && (
          <div className="pagination-bar" style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "15px", marginTop: "24px" }}>
            <button
              className="btn btn-outline btn-sm"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            >
              Previous
            </button>
            <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 500 }}>
              Page <strong>{currentPage}</strong> of {totalPages}
            </span>
            <button
              className="btn btn-outline btn-sm"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* ── Floating Action Button ── */}
      <button
        className="citizen-fab"
        onClick={() => setShowModal(true)}
        title="Report an Issue"
        id="report-issue-fab"
      >
        <Plus size={24} />
      </button>

      {/* ── Add Complaint Modal ── */}
      {showModal && (
        <AddComplaint
          wardId={user?.ward_id}
          wardName={wardObj?.name || `Ward #${user?.ward_id}`}
          locality={user?.locality_description || ""}
          onClose={() => setShowModal(false)}
          onSuccess={() => { setShowModal(false); fetchComplaintsAndStats(wardScope); }}
        />
      )}

      {/* ── Lightbox Overlay ── */}
      {lightboxMedia && (
        <div
          onClick={() => setLightboxMedia(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px"
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: "relative",
              maxWidth: "90%",
              maxHeight: "90%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <button
              onClick={() => setLightboxMedia(null)}
              style={{
                position: "absolute",
                top: "-40px",
                right: "0",
                background: "none",
                border: "none",
                color: "#fff",
                fontSize: "24px",
                cursor: "pointer",
                fontWeight: 300
              }}
            >
              ✕ Close
            </button>
            {lightboxMedia.type === "image" ? (
              <img
                src={lightboxMedia.url}
                alt="Full size media"
                style={{
                  maxWidth: "100%",
                  maxHeight: "80vh",
                  borderRadius: "8px",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                }}
              />
            ) : (
              <video
                src={lightboxMedia.url}
                controls
                autoPlay
                style={{
                  maxWidth: "100%",
                  maxHeight: "80vh",
                  borderRadius: "8px",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
