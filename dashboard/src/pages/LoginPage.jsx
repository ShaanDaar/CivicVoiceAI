/**
 * LoginPage.jsx — Login form for all user roles.
 *
 * On success:
 *   - role === "citizen"       → navigate to /home
 *   - role === "admin"         → navigate to /admin
 *   - role === "admin_pending" → navigate to /status  (answers user question 1)
 *   - role === "rejected"      → show rejection message, don't log in
 */

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Building2, Mail, Lock, LogIn, Eye, EyeOff } from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || "Login failed. Check your credentials.");
        return;
      }

      // Rejected accounts cannot log in — show a clear message
      if (data.role === "rejected") {
        setError("Your admin application was rejected. Please contact the administrator.");
        return;
      }

      // Persist auth in context + localStorage
      login(data.access_token, data.role, {
        user_id: data.user_id,
        full_name: data.full_name,
        ward_id: data.ward_id,
      });

      // Route by role
      if (data.role === "admin") navigate("/admin", { replace: true });
      else if (data.role === "admin_pending") navigate("/status", { replace: true });
      else navigate("/home", { replace: true });

    } catch (err) {
      setError("Cannot connect to backend. Is the server running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      {/* Background decorative blobs */}
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />

      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <Building2 size={32} />
          <span>CivicVoice AI</span>
        </div>
        <h1 className="auth-heading">Welcome back</h1>
        <p className="auth-sub">Sign in to continue to your dashboard</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          {/* Email */}
          <div className="auth-field">
            <label htmlFor="login-email">Email address</label>
            <div className="auth-input-wrapper">
              <Mail size={16} className="auth-input-icon" />
              <input
                id="login-email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password */}
          <div className="auth-field">
            <label htmlFor="login-password">Password</label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="auth-input-icon" />
              <input
                id="login-password"
                type={showPass ? "text" : "password"}
                placeholder="Your password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                className="auth-eye-btn"
                onClick={() => setShowPass(v => !v)}
                tabIndex={-1}
              >
                {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary auth-submit"
            disabled={loading}
            id="login-submit-btn"
          >
            {loading ? (
              <span className="auth-spinner" />
            ) : (
              <><LogIn size={16} /> Sign In</>
            )}
          </button>
        </form>

        <p className="auth-footer-link">
          Don't have an account?{" "}
          <Link to="/signup">Create one →</Link>
        </p>
        <p className="auth-footer-link" style={{ marginTop: "6px" }}>
          <Link to="/">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}
