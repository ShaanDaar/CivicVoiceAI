/**
 * LandingPage.jsx — Public-facing marketing page for CivicVoice AI.
 *
 * Sections:
 *   1. Hero — bold headline + animated counter stats pulled from live API
 *   2. How It Works — 3 visual steps (Report → Route → Resolve)
 *   3. CTA — Join as Citizen | Admin Portal buttons
 *
 * No auth required. Visitors land here first.
 */

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Mic, Route, CheckCircle2, Building2, ArrowRight,
  Users, Zap, ShieldCheck, Globe, BarChart3
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

// Animated counter hook — counts up from 0 to target over ~1.2s
function useCounter(target, duration = 1200) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!target) return;
    let start = 0;
    const step = Math.ceil(duration / target);
    const timer = setInterval(() => {
      start += 1;
      setCount(start);
      if (start >= target) clearInterval(timer);
    }, step);
    return () => clearInterval(timer);
  }, [target, duration]);
  return count;
}

export default function LandingPage() {
  const [stats, setStats] = useState({ total: 0, resolved: 0, wards: 0 });

  // Fetch live stats from the backend
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/complaints`).then(r => r.json()).catch(() => []),
      fetch(`${API_BASE}/wards`).then(r => r.json()).catch(() => []),
    ]).then(([complaints, wards]) => {
      const resolved = complaints.filter(c => c.status === "resolved").length;
      setStats({ total: complaints.length, resolved, wards: wards.length });
    });
  }, []);

  const totalCount = useCounter(stats.total);
  const resolvedCount = useCounter(stats.resolved);
  const wardsCount = useCounter(stats.wards);

  return (
    <div className="landing-page">
      {/* ── Top Nav ── */}
      <header className="landing-nav">
        <div className="landing-nav-brand">
          <Building2 size={24} />
          <span>CivicVoice AI</span>
        </div>
        <div className="landing-nav-links">
          <Link to="/login" className="landing-nav-link">Sign In</Link>
          <Link to="/signup" className="landing-nav-cta">Get Started</Link>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="landing-hero">
        <div className="hero-badge">
          <Globe size={14} /> SDG 11 — Sustainable Cities &amp; Communities
        </div>
        <h1 className="hero-title">
          Your Voice,<br />
          <span className="hero-title-accent">Your City.</span>
        </h1>
        <p className="hero-subtitle">
          CivicVoice AI turns everyday complaints into accountable municipal action.
          Report water leaks, power outages, and sanitation issues in <strong>your own language</strong> —
          our AI routes them to the right department instantly.
        </p>
        <div className="hero-cta-group">
          <Link to="/signup" className="btn btn-primary btn-lg">
            Report an Issue <ArrowRight size={18} />
          </Link>
          <Link to="/login" className="btn btn-outline btn-lg">
            Sign In
          </Link>
        </div>

        {/* Live Stats Row */}
        <div className="hero-stats">
          <div className="hero-stat">
            <span className="hero-stat-number">{totalCount}</span>
            <span className="hero-stat-label">Complaints Filed</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat-number">{resolvedCount}</span>
            <span className="hero-stat-label">Resolved</span>
          </div>
          <div className="hero-stat-divider" />
          <div className="hero-stat">
            <span className="hero-stat-number">{wardsCount}</span>
            <span className="hero-stat-label">Active Wards</span>
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="landing-how">
        <p className="section-eyebrow">How It Works</p>
        <h2 className="section-title">From Complaint to Resolution in 3 Steps</h2>
        <div className="how-steps">
          <div className="how-step">
            <div className="how-step-icon" style={{ background: "linear-gradient(135deg, #8C624E, #C4846A)" }}>
              <Mic size={28} color="#fff" />
            </div>
            <div className="how-step-number">01</div>
            <h3>Report</h3>
            <p>Submit a voice note or text complaint in any language — Hindi, Marathi, Kannada, or English. Our AI handles the rest.</p>
          </div>
          <div className="how-step-arrow"><ArrowRight size={24} /></div>
          <div className="how-step">
            <div className="how-step-icon" style={{ background: "linear-gradient(135deg, #1565C0, #1976D2)" }}>
              <Route size={28} color="#fff" />
            </div>
            <div className="how-step-number">02</div>
            <h3>Route</h3>
            <p>The LangGraph AI agent classifies the issue, scores urgency 1–5, and routes directly to Water, Electricity, or Sanitation departments.</p>
          </div>
          <div className="how-step-arrow"><ArrowRight size={24} /></div>
          <div className="how-step">
            <div className="how-step-icon" style={{ background: "linear-gradient(135deg, #2E7D32, #388E3C)" }}>
              <CheckCircle2 size={28} color="#fff" />
            </div>
            <div className="how-step-number">03</div>
            <h3>Resolve</h3>
            <p>Admins triage and update ticket status. Every ward's response time is tracked publicly — no more accountability gaps.</p>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="landing-features">
        <div className="feature-card">
          <Zap size={24} className="feature-icon" />
          <h3>AI-Powered Classification</h3>
          <p>Gemini + LangGraph classify complaints in milliseconds with full reasoning transparency.</p>
        </div>
        <div className="feature-card">
          <Globe size={24} className="feature-icon" />
          <h3>Multilingual Voice Intake</h3>
          <p>Speak in your mother tongue — the system transcribes and translates automatically.</p>
        </div>
        <div className="feature-card">
          <BarChart3 size={24} className="feature-icon" />
          <h3>Public Accountability</h3>
          <p>Ward-level resolution times are visible to everyone. No more hidden backlogs.</p>
        </div>
        <div className="feature-card">
          <ShieldCheck size={24} className="feature-icon" />
          <h3>Verified Admin Access</h3>
          <p>Municipal admins submit credentials for verification. Approvals are documented and audited.</p>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="landing-cta-banner">
        <h2>Ready to make your city better?</h2>
        <p>Join as a citizen to report issues, or apply for admin access to manage your ward's complaints.</p>
        <div className="hero-cta-group">
          <Link to="/signup" className="btn btn-primary btn-lg">
            <Users size={18} /> Join as Citizen
          </Link>
          <Link to="/signup?role=admin" className="btn btn-outline-dark btn-lg">
            <ShieldCheck size={18} /> Admin Portal
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <p>CivicVoice AI — Built for SDG 11 · Powered by Google Gemini + LangGraph</p>
      </footer>
    </div>
  );
}
