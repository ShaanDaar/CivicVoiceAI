/**
 * App.jsx — Router shell for CivicVoice AI.
 *
 * All routing decisions live here. Pages themselves handle their own data fetching.
 *
 * Route map:
 *   /           → LandingPage        (public)
 *   /login      → LoginPage          (public)
 *   /signup     → SignupPage         (public)
 *   /home       → CitizenHome        (citizen only)
 *   /status     → ApplicationStatusPage (admin_pending only)
 *   /admin      → AdminDashboard     (admin only)
 *   *           → redirect to /
 */

import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { ProtectedRoute } from "./context/AuthContext";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import CitizenHome from "./pages/CitizenHome";
import ApplicationStatusPage from "./pages/ApplicationStatusPage";
import AdminDashboard from "./pages/AdminDashboard";

export default function App() {
  return (
    <Routes>
      {/* ── Public routes ── */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      {/* ── Citizen protected route ── */}
      <Route
        path="/home"
        element={
          <ProtectedRoute allowedRoles={["citizen"]}>
            <CitizenHome />
          </ProtectedRoute>
        }
      />

      {/* ── Pending admin status page ── */}
      <Route
        path="/status"
        element={
          <ProtectedRoute allowedRoles={["admin_pending", "admin"]}>
            <ApplicationStatusPage />
          </ProtectedRoute>
        }
      />

      {/* ── Admin dashboard ── */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      {/* ── Fallback ── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
