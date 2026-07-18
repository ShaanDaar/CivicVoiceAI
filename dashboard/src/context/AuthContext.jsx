/**
 * AuthContext.jsx — Global authentication state for CivicVoice AI.
 *
 * Stores the JWT token, user profile, and role in React Context + localStorage
 * so any page can access them without prop-drilling.
 *
 * Also exports:
 *   - useAuth() — hook to consume auth state
 *   - ProtectedRoute — wraps routes with role enforcement
 */

import React, { createContext, useContext, useState, useEffect } from "react";
import { Navigate } from "react-router-dom";

const AuthContext = createContext(null);

const STORAGE_KEY = "civicvoice_auth";

export function AuthProvider({ children }) {
  // Restore persisted auth on first load
  const [auth, setAuth] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : { token: null, role: null, user: null };
    } catch {
      return { token: null, role: null, user: null };
    }
  });

  /**
   * Called after successful login.
   * @param {string} token  — JWT access token
   * @param {string} role   — "citizen" | "admin" | "admin_pending"
   * @param {object} user   — { user_id, full_name, ward_id, email }
   */
  const login = (token, role, user) => {
    const next = { token, role, user };
    setAuth(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  /** Clear all auth state and redirect to login. */
  const logout = () => {
    setAuth({ token: null, role: null, user: null });
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

/** Convenience hook. */
export function useAuth() {
  return useContext(AuthContext);
}

/**
 * ProtectedRoute — wraps a page component with role-based access control.
 *
 * Props:
 *   children      — the page component to render if auth passes
 *   allowedRoles  — array of roles that may access this route (e.g. ["admin"])
 *                   If null/empty, any authenticated user is allowed.
 *   redirectTo    — path to send the user if they fail the check (default: "/login")
 */
export function ProtectedRoute({ children, allowedRoles, redirectTo = "/login" }) {
  const { token, role } = useAuth();

  // Not logged in → go to login
  if (!token) return <Navigate to={redirectTo} replace />;

  // Role-restricted route — check membership
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(role)) {
    // admin_pending users always land on /status page
    if (role === "admin_pending") return <Navigate to="/status" replace />;
    // citizens trying to access admin → back to home
    if (role === "citizen") return <Navigate to="/home" replace />;
    // fallback
    return <Navigate to="/" replace />;
  }

  return children;
}
