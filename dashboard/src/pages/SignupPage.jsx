/**
 * SignupPage.jsx — Registration page with two tabs: Citizen and Admin Applicant.
 *
 * Citizen Tab:
 *   - Full Name, Email, Phone, Password, Ward, Locality
 *   - POSTs to /auth/register → success → redirect to /login
 *
 * Admin Tab:
 *   - Same fields + verification document upload (PDF/image)
 *   - Account created as admin_pending
 *   - Clear notice: "Account requires approval before access"
 *   - POSTs to /auth/register/admin (multipart/form-data)
 *   - On success → redirect to /login?registered=admin
 */

import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Building2, User, Mail, Phone, Lock, MapPin, Upload,
  Eye, EyeOff, AlertCircle, CheckCircle2
} from "lucide-react";
import { API_BASE } from "../config";

export default function SignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Pre-select Admin tab if ?role=admin in URL (from landing page CTA)
  const [tab, setTab] = useState(searchParams.get("role") === "admin" ? "admin" : "citizen");

  const [wards, setWards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Shared fields
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [wardId, setWardId] = useState("");
  const [locality, setLocality] = useState("");

  // Admin-only
  const [docFile, setDocFile] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/wards`)
      .then(r => r.json())
      .then(setWards)
      .catch(() => {});
  }, []);

  const resetForm = () => {
    setFullName(""); setEmail(""); setPhone(""); setPassword("");
    setWardId(""); setLocality(""); setDocFile(null); setError("");
  };

  const handleCitizenSubmit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess(""); setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email,
          phone: phone || null,
          password,
          ward_id: parseInt(wardId),
          locality_description: locality || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Registration failed."); return; }
      setSuccess("Account created! Redirecting to sign in…");
      setTimeout(() => navigate("/login"), 1800);
    } catch {
      setError("Cannot reach backend. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminSubmit = async (e) => {
    e.preventDefault();
    setError(""); setSuccess(""); setLoading(true);

    if (!docFile) { setError("Please upload a verification document."); setLoading(false); return; }

    const formData = new FormData();
    formData.append("full_name", fullName);
    formData.append("email", email);
    if (phone) formData.append("phone", phone);
    formData.append("password", password);
    formData.append("ward_id", wardId);
    if (locality) formData.append("locality_description", locality);
    formData.append("verification_doc", docFile);

    try {
      const res = await fetch(`${API_BASE}/auth/register/admin`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Registration failed."); return; }
      setSuccess("Application submitted! Your account is pending review. You can track your status after signing in.");
      setTimeout(() => navigate("/login"), 3000);
    } catch {
      setError("Cannot reach backend. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />

      <div className="auth-card auth-card-wide">
        <div className="auth-logo">
          <Building2 size={30} />
          <span>CivicVoice AI</span>
        </div>
        <h1 className="auth-heading">Create your account</h1>

        {/* Role Tabs */}
        <div className="auth-tabs">
          <button
            id="tab-citizen"
            className={`auth-tab ${tab === "citizen" ? "active" : ""}`}
            onClick={() => { setTab("citizen"); resetForm(); }}
          >
            🏘️ Citizen
          </button>
          <button
            id="tab-admin"
            className={`auth-tab ${tab === "admin" ? "active" : ""}`}
            onClick={() => { setTab("admin"); resetForm(); }}
          >
            🛡️ Admin Applicant
          </button>
        </div>

        {/* Admin notice */}
        {tab === "admin" && (
          <div className="auth-notice admin-notice">
            <AlertCircle size={16} />
            <div>
              <strong>Admin accounts require approval.</strong> Your application and uploaded
              document will be reviewed by a verified admin before you gain dashboard access.
              You can track your application status after signing in.
            </div>
          </div>
        )}

        {/* Success / Error banners */}
        {success && (
          <div className="auth-notice success-notice">
            <CheckCircle2 size={16} />
            <span>{success}</span>
          </div>
        )}
        {error && <div className="auth-error">{error}</div>}

        {/* ── Form ── */}
        <form
          className="auth-form"
          onSubmit={tab === "citizen" ? handleCitizenSubmit : handleAdminSubmit}
        >
          {/* Row 1: Name + Email */}
          <div className="auth-row">
            <div className="auth-field">
              <label htmlFor="signup-name">Full Name *</label>
              <div className="auth-input-wrapper">
                <User size={15} className="auth-input-icon" />
                <input id="signup-name" type="text" placeholder="Priya Sharma" value={fullName}
                  onChange={e => setFullName(e.target.value)} required />
              </div>
            </div>
            <div className="auth-field">
              <label htmlFor="signup-email">Email *</label>
              <div className="auth-input-wrapper">
                <Mail size={15} className="auth-input-icon" />
                <input id="signup-email" type="email" placeholder="priya@example.com" value={email}
                  onChange={e => setEmail(e.target.value)} required />
              </div>
            </div>
          </div>

          {/* Row 2: Phone + Password */}
          <div className="auth-row">
            <div className="auth-field">
              <label htmlFor="signup-phone">Phone</label>
              <div className="auth-input-wrapper">
                <Phone size={15} className="auth-input-icon" />
                <input id="signup-phone" type="tel" placeholder="+91 98765 43210" value={phone}
                  onChange={e => setPhone(e.target.value)} />
              </div>
            </div>
            <div className="auth-field">
              <label htmlFor="signup-password">Password *</label>
              <div className="auth-input-wrapper">
                <Lock size={15} className="auth-input-icon" />
                <input id="signup-password" type={showPass ? "text" : "password"} placeholder="Min. 8 characters"
                  value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
                <button type="button" className="auth-eye-btn" onClick={() => setShowPass(v => !v)} tabIndex={-1}>
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
          </div>

          {/* Row 3: Ward + Locality */}
          <div className="auth-row">
            <div className="auth-field">
              <label htmlFor="signup-ward">Ward *</label>
              <div className="auth-input-wrapper">
                <MapPin size={15} className="auth-input-icon" />
                <select id="signup-ward" value={wardId} onChange={e => setWardId(e.target.value)} required>
                  <option value="">Select your ward…</option>
                  {wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              </div>
            </div>
            <div className="auth-field">
              <label htmlFor="signup-locality">Locality / Address</label>
              <div className="auth-input-wrapper">
                <MapPin size={15} className="auth-input-icon" />
                <input id="signup-locality" type="text" placeholder="e.g. Flat 4B, near bus stand"
                  value={locality} onChange={e => setLocality(e.target.value)} />
              </div>
            </div>
          </div>

          {/* Admin: document upload */}
          {tab === "admin" && (
            <div className="auth-field">
              <label htmlFor="signup-doc">
                Verification Document * <span className="auth-sub-label">(Municipal ID, Appointment Letter — PDF or image)</span>
              </label>
              <label htmlFor="signup-doc" className="auth-file-label">
                <Upload size={16} />
                {docFile ? docFile.name : "Click to upload document…"}
                <input
                  id="signup-doc"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={e => setDocFile(e.target.files[0] || null)}
                  style={{ display: "none" }}
                />
              </label>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary auth-submit"
            disabled={loading}
            id="signup-submit-btn"
          >
            {loading ? <span className="auth-spinner" /> : tab === "citizen" ? "Create Account" : "Submit Application"}
          </button>
        </form>

        <p className="auth-footer-link">
          Already have an account? <Link to="/login">Sign in →</Link>
        </p>
        <p className="auth-footer-link" style={{ marginTop: "6px" }}>
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
