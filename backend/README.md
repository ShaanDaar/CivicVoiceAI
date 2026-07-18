# CivicVoice AI Backend API

This directory contains the FastAPI-based application backend skeleton for CivicVoice AI. 

## Features
- **SQLite Database Integration** (via SQLAlchemy)
- **Automatic Database Creation & Seeding**: Seeds the database with 5 sample wards and department contacts on startup.
- **REST Endpoints**:
  - `POST /complaints` - Submit a new citizen complaint.
  - `GET /complaints` - Retrieve list of complaints (supports filtering by `ward_id` and `status`).
  - `PATCH /complaints/{id}/status` - Transition complaint status (triggers a new status history entry).
  - `GET /complaints/{id}/resolution-time` - Computes and returns the resolution time in seconds dynamically.
  - `GET /wards` - Retrieve sample wards.
  - `GET /departments` - Retrieve sample departments.

---

## Directory Structure
```text
backend/
├── app/
│   ├── __init__.py
│   ├── database.py   # Database connection & engine setup
│   ├── models.py     # SQLAlchemy models & dynamic resolution math
│   ├── schemas.py    # Pydantic schemas for request/response serialization
│   ├── seed.py       # Initial seed data for Wards and Departments
│   └── main.py       # FastAPI application and route handlers
├── requirements.txt  # Python packages list
└── README.md         # Setup and walkthrough instructions
```

---

## Setup & Running Instructions

### 1. Create a Virtual Environment (Optional but Recommended)
Run the following in your terminal from the `backend/` directory:
```bash
python -m venv venv
```
Activate it:
- **Windows (Command Prompt)**:
  ```cmd
  venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  venv\Scripts\Activate.ps1
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 4. Interactive Documentation
Once started, you can access:
- Swagger Interactive Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Alternative docs (ReDoc): [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
