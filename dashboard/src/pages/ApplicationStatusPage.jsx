/**
 * ApplicationStatusPage.jsx — Dedicated page for admin_pending users.
 *
 * Answers Question 1: "How will the new admin signing up view and track their application status?"
 *
 * This page is shown when an admin_pending user logs in (LoginPage redirects them here).
 * They can return any time by logging in — their JWT is valid and the page fetches their
 * current status from GET /auth/me on every visit.
 *
 * Status states:
 *   - admin_pending  → animated "Under Review" indicator + submitted details
 *   - admin          → shouldn't land here (redirect to /admin), but handled gracefully
 *   - rejected       → rejection reason shown with instructions
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Navbar from "../components/Navbar";
import {
  Clock, CheckCircle2, XCircle, FileText, User, Mail,
  MapPin, RefreshCw, Building2, AlertCircle
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

export default function ApplicationStatusPage() {
  const { token, role, login, user: authUser } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [ward, setWard] = useState(null);
  const [fetching, setFetching] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  /**
   * Fetch the latest profile from the server on every visit.
   * This is how the pending admin "tracks" their status — they log in,
   * land here, and see the live state of their application.
   */
  const fetchProfile = async () => {
    setFetching(true);
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch profile");
      const data = await res.json();
      setProfile(data);
      setLastChecked(new Date());

      // If the admin was approved since last login, update context and redirect
      if (data.role === "admin") {
        login(token, "admin", { ...authUser, user_id: data.id, full_name: data.full_name });
        navigate("/admin", { replace: true });
        return;
      }

      // Fetch ward name for display
      if (data.ward_id) {
        const wRes = await fetch(`${API_BASE}/wards`);
        const wards = await wRes.json();
        setWard(wards.find(w => w.id === data.ward_id) || null);
      }
    } catch (err) {
      console.error("Profile fetch error:", err);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  // ── Status config ──
  const statusConfig = {
    admin_pending: {
      icon: <Clock size={40} />,
      color: "#EF6C00",
      bgColor: "rgba(239, 108, 0, 0.08)",
      borderColor: "rgba(239, 108, 0, 0.2)",
      label: "Under Review",
      description: "Your application has been received and is currently being reviewed by a verified administrator. This typically takes 1–3 business days.",
    },
    rejected: {
      icon: <XCircle size={40} />,
      color: "#C62828",
      bgColor: "rgba(198, 40, 40, 0.06)",
      borderColor: "rgba(198, 40, 40, 0.2)",
      label: "Application Rejected",
      description: "Your admin application was not approved. Please review the reason below and contact your municipal office if you believe this is an error.",
    },
    admin: {
      icon: <CheckCircle2 size={40} />,
      color: "#2E7D32",
      bgColor: "rgba(46, 125, 50, 0.08)",
      borderColor: "rgba(46, 125, 50, 0.2)",
      label: "Approved!",
      description: "Your application was approved. Redirecting you to the admin dashboard…",
    },
  };

  const config = statusConfig[profile?.role] || statusConfig.admin_pending;

  return (
    <div className="page-wrapper">
      <Navbar />

      <div className="status-page">
        {/* Header */}
        <div className="status-page-header">
          <h1>Admin Application Status</h1>
          <p>Check back here anytime after signing in to see your application progress.</p>
        </div>

        {fetching && !profile ? (
          <div className="status-loading">
            <RefreshCw size={24} className="spinner-icon" />
            <span>Loading your application…</span>
          </div>
        ) : profile ? (
          <div className="status-content">

            {/* ── Status Card ── */}
            <div
              className="status-card"
              style={{ borderColor: config.borderColor, background: config.bgColor }}
            >
              <div className="status-icon" style={{ color: config.color }}>
                {config.icon}
              </div>

              {/* Animated pulse ring for pending */}
              {profile.role === "admin_pending" && (
                <div className="status-pulse-ring" style={{ borderColor: config.color }} />
              )}

              <h2 className="status-label" style={{ color: config.color }}>
                {config.label}
              </h2>
              <p className="status-description">{config.description}</p>

              {/* Rejection reason */}
              {profile.role === "rejected" && profile.rejection_reason && (
                <div className="rejection-reason">
                  <AlertCircle size={16} />
                  <div>
                    <strong>Reason:</strong> {profile.rejection_reason}
                  </div>
                </div>
              )}

              {/* Progress timeline for pending */}
              {profile.role === "admin_pending" && (
                <div className="status-timeline">
                  <div className="timeline-step done">
                    <div className="timeline-dot" />
                    <span>Application Submitted</span>
                  </div>
                  <div className="timeline-connector done" />
                  <div className="timeline-step active">
                    <div className="timeline-dot pulsing" />
                    <span>Under Admin Review</span>
                  </div>
                  <div className="timeline-connector" />
                  <div className="timeline-step">
                    <div className="timeline-dot" />
                    <span>Account Activated</span>
                  </div>
                </div>
              )}
            </div>

            {/* ── Application Details Card ── */}
            <div className="card status-details-card">
              <h3 className="status-details-title">
                <FileText size={18} /> Your Submitted Application
              </h3>
              <div className="status-details-grid">
                <div className="status-detail-row">
                  <User size={15} className="status-detail-icon" />
                  <span className="status-detail-label">Full Name</span>
                  <span className="status-detail-value">{profile.full_name}</span>
                </div>
                <div className="status-detail-row">
                  <Mail size={15} className="status-detail-icon" />
                  <span className="status-detail-label">Email</span>
                  <span className="status-detail-value">{profile.email}</span>
                </div>
                {profile.phone && (
                  <div className="status-detail-row">
                    <span className="status-detail-icon">📞</span>
                    <span className="status-detail-label">Phone</span>
                    <span className="status-detail-value">{profile.phone}</span>
                  </div>
                )}
                <div className="status-detail-row">
                  <MapPin size={15} className="status-detail-icon" />
                  <span className="status-detail-label">Ward</span>
                  <span className="status-detail-value">{ward?.name || `Ward #${profile.ward_id}`}</span>
                </div>
                {profile.locality_description && (
                  <div className="status-detail-row">
                    <Building2 size={15} className="status-detail-icon" />
                    <span className="status-detail-label">Locality</span>
                    <span className="status-detail-value">{profile.locality_description}</span>
                  </div>
                )}
                <div className="status-detail-row">
                  <FileText size={15} className="status-detail-icon" />
                  <span className="status-detail-label">Document</span>
                  <span className="status-detail-value" style={{ color: "var(--color-success)" }}>
                    ✓ Uploaded
                  </span>
                </div>
                <div className="status-detail-row">
                  <Clock size={15} className="status-detail-icon" />
                  <span className="status-detail-label">Submitted</span>
                  <span className="status-detail-value">
                    {new Date(profile.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            {/* Refresh button */}
            <div className="status-footer">
              <button className="btn btn-outline" onClick={fetchProfile} disabled={fetching}>
                <RefreshCw size={15} className={fetching ? "spinner-icon" : ""} />
                Check for Updates
              </button>
              {lastChecked && (
                <span className="status-last-checked">
                  Last checked: {lastChecked.toLocaleTimeString()}
                </span>
              )}
            </div>

            {/* Guidance for rejected users */}
            {profile.role === "rejected" && (
              <div className="auth-notice admin-notice" style={{ marginTop: "16px" }}>
                <AlertCircle size={16} />
                <div>
                  To reapply, please <a href="/signup?role=admin">create a new admin application</a> with
                  updated credentials, or contact your municipal office directly.
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="status-loading">Could not load your profile. Please try refreshing.</div>
        )}
      </div>
    </div>
  );
}
