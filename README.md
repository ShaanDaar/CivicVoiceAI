# CivicVoice AI 🏛️

**CivicVoice AI** is an agentic AI system designed for **SDG 11 (Sustainable Cities & Settlements)**. The platform allows residents of informal urban settlements to register infrastructure complaints (water, drainage, electricity, sanitation) via text or simulated voice notes. It automates classification, tags urgency levels using a weighted safety rubric, assigns tasks to correct municipal departments, tracks administrative resolution speeds, and reports metrics on a public dashboard.

---

## 🏗️ System Architecture

1. **Backend (Python & FastAPI):** Serves API endpoints for complaint persistence, ward listings, department assignments, and resolution patching.
2. **AI Agent reasoning (LangGraph & Gemini API):** Intercepts raw complains, determines language/rubric score/category using `gemini-3.1-flash-lite`, and logs reasoning details. Includes a rule-based weighted keyword classifier fallback.
3. **Frontend Dashboard (Vite + React.js):** Provides a visual overview of active complaints, allows admins to patch ticket stages, and hosts a citizen intake simulator.
4. **Intake Orchestration (n8n Workflows):** Integrates WhatsApp/webhook triggers with the FastAPI endpoint (import JSON specified in `n8n_integration.md`).

---

## 📂 Project Structure

```text
CivicVoiceAI/
├── backend/                       # Python FastAPI Backend
│   ├── app/
│   │   ├── agent/                 # LangGraph classifier & LLM configs
│   │   ├── database.py            # SQLite engine configuration
│   │   ├── models.py              # SQLAlchemy DB Schemas
│   │   ├── main.py                # FastAPI endpoints & CORS
│   │   └── seed.py                # Initial administrative wards/departments
│   ├── .env                       # API Credentials (contains GEMINI_API_KEY)
│   ├── test_agent.py              # Live LLM categorization test runner
│   └── requirements.txt
├── dashboard/                     # Vite React Frontend
│   ├── src/
│   │   ├── App.jsx                # Dashboard state & Simulated portal
│   │   ├── index.css              # Custom slate dark style tokens
│   │   └── App.css                # Layout layout grid details
│   ├── index.html
│   └── package.json
├── .gitignore                     # Git credential safeguards
└── README.md                      # Presentation Setup Guide
```

---

## 🚀 Setup & Launch Guide

### Prerequisites
- Python 3.10+
- Node.js (LTS version)

---

### Step 1: Initialize the Backend Server

1. **Navigate to the backend directory and create a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   ```
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure API Keys:**
   Create a `.env` file in the `backend/` directory:
   ```properties
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
4. **Seed Database and Start backend:**
   ```bash
   venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The database `civicvoice.db` will populate automatically with Mumbai administrative wards and departments.*

---

### Step 2: Initialize the React Dashboard

1. **Open a new terminal shell and navigate to the dashboard:**
   ```bash
   cd dashboard
   ```
2. **Install dependencies:**
   ```bash
   npm install
   ```
3. **Start the Vite client:**
   ```bash
   npm run dev -- --host 127.0.0.1 --port 3000
   ```
4. **Open the browser:**
   Open [http://127.0.0.1:3000](http://127.0.0.1:3000) to view the live dashboard.

---

### Step 3: Run Classification Integration Tests

To test the LangGraph routing engine and Gemini prompt mapping directly:
```bash
cd backend
venv\Scripts\python test_agent.py
```
This prints the categories, 1-5 urgency scores, and Gemini's detailed reasoning across 5 live test cases.

---

## 📊 Demo Presentation Flow

1. **API Link Verification:** Check that the indicator glows green as `LIVE BACKEND LINKED`.
2. **Accountability Tracking:** Review the **Ward Accountability** metrics indicating resolved ticket average resolution delays.
3. **Citizen Intake simulation:** Type a complaint (e.g., *"My alley is flooded since yesterday from a burst pipe."*) in the simulator portal and click **Submit Simulated Webhook**. 
4. **Dynamic Triage:** Observe the classification box resolving the issue type (Category: `water`, Urgency: `4/5`), showing Gemini's reasoning. The complaint immediately shifts into the explorer list.
5. **Interactive Resolutions:** Toggle dropdown statuses in the complaints cards list to automatically close complaints or patch active workflow stages in real-time.
