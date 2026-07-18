# AGENTS.md — CivicVoice AI

## Project
An agentic AI system for SDG 11 (Sustainable Cities). Residents of informal 
urban settlements report civic infrastructure complaints (water, drainage, 
electricity, sanitation) via voice note or photo in local language. The system 
classifies, routes to the correct municipal department, and tracks response 
time on a public dashboard.

## Stack
- Orchestration: n8n (self-hosted or n8n cloud) for intake workflows, notifications, scheduling
- Agent reasoning: LangGraph (Python) for classification, severity triage, routing logic
- Backend: Python (FastAPI) 
- Frontend dashboard: simple React or Next.js app showing complaint status by ward
- Database: PostgreSQL (or SQLite for prototype stage) — table for complaints, wards, departments, status history
- Messaging channel for demo: WhatsApp Business API sandbox or a simulated webhook (no real WhatsApp integration required for MVP)

## Critical Rules
1. This is a prototype/demo for an internship review — prioritize working end-to-end flow over production hardening.
2. Use only synthetic/sample data — never wire up real citizen data or real municipal systems.
3. Every complaint record must include: raw input, detected language, extracted issue type, urgency score, assigned department, ward, timestamp, status, resolution time.
4. Keep LangGraph logic and n8n workflows loosely coupled — LangGraph should be callable as an API endpoint that n8n triggers.
5. Explain each major decision in code comments — I need to understand and present this, not just submit it.

## Preferences
- Python for backend/agent logic, TypeScript/React for dashboard
- Keep the LLM classification logic isolated in its own module so I can swap models easily
- Generate a README with setup instructions after each major milestone