/**
 * Navbar.jsx — Shared top navigation for authenticated pages.
 *
 * Shows:
 *   - CivicVoice logo + role badge
 *   - Page links based on role
 *   - Logged-in user's name
 *   - Logout button
 */

import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Building2, LogOut, Home, ShieldCheck, Clock } from "lucide-react";

export default function Navbar() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const roleBadgeColor = {
    admin: "#2E7D32",
    admin_pending: "#EF6C00",
    citizen: "#1565C0",
  }[role] || "#555";

  const roleLabel = {
    admin: "Admin",
    admin_pending: "Pending Approval",
    citizen: "Citizen",
  }[role] || role;

  return (
    <nav className="navbar">
      {/* Brand */}
      <Link to={role === "admin" ? "/admin" : role === "citizen" ? "/home" : "/status"} className="navbar-brand">
        <Building2 size={22} />
        <span>CivicVoice AI</span>
      </Link>

      {/* Links */}
      <div className="navbar-links">
        {role === "citizen" && (
          <Link
            to="/home"
            className={`navbar-link ${location.pathname === "/home" ? "active" : ""}`}
          >
            <Home size={16} /> My Ward
          </Link>
        )}
        {role === "admin" && (
          <Link
            to="/admin"
            className={`navbar-link ${location.pathname === "/admin" ? "active" : ""}`}
          >
            <ShieldCheck size={16} /> Triage Dashboard
          </Link>
        )}
        {role === "admin_pending" && (
          <Link
            to="/status"
            className={`navbar-link ${location.pathname === "/status" ? "active" : ""}`}
          >
            <Clock size={16} /> Application Status
          </Link>
        )}
      </div>

      {/* User info + logout */}
      <div className="navbar-user">
        <div className="navbar-user-info">
          <span className="navbar-user-name">{user?.full_name || "User"}</span>
          <span className="navbar-role-badge" style={{ background: roleBadgeColor }}>
            {roleLabel}
          </span>
        </div>
        <button className="navbar-logout-btn" onClick={handleLogout} title="Sign out">
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </nav>
  );
}
