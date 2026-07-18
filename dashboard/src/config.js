/**
 * config.js — Shared frontend configuration.
 *
 * Resolves the API Base URL from environment variables or uses the default local backend port.
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
