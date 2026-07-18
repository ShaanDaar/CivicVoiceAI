"""
main.py — FastAPI application for CivicVoice AI.

Architecture:
- /auth/*        — Registration, login, profile, admin approval
- /wards         — Ward listing (public)
- /departments   — Department listing (public)
- /complaints    — Complaint CRUD (create: JWT; list: public; status update: admin)
- /classify      — LangGraph classification (JWT or intake key)
- /transcribe    — Gemini audio transcription (JWT or intake key)
- /verify-password — Legacy admin session token (for developer/first-admin bootstrap)
"""

from contextlib import asynccontextmanager
from typing import List, Optional
import os
import secrets
import shutil

from fastapi import (
    FastAPI, Depends, HTTPException, Query,
    status, UploadFile, File, Form, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal, get_db
from .models import Complaint, StatusHistory, Ward, Department, User
from .schemas import (
    ComplaintCreate, ComplaintResponse, ComplaintUpdateStatus, ComplaintStatsResponse,
    WardResponse, DepartmentResponse,
    ClassifyRequest, ClassifyResponse, TranscribeResponse,
    UserCreate, UserResponse, UserLogin, TokenResponse,
    AdminPendingResponse, AdminApproveRequest,
    SocialDraftRequest, SocialDraftResponse,
)
from .seed import seed_initial_data
from .agent.graph import agent_graph
from .auth import (
    hash_password, verify_password as verify_pw,
    create_access_token,
    get_current_user, get_current_user_optional, require_admin,
)

# ── Load .env for local development ───────────────────────────────────────────
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_paths = [os.path.join(root_dir, ".env"), os.path.join(root_dir, "venv", ".env")]
for ep in env_paths:
    if os.path.exists(ep):
        with open(ep, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
        break

# ── Startup validation ─────────────────────────────────────────────────────────
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError(
        "CRITICAL CONFIGURATION ERROR: ADMIN_PASSWORD environment variable is not set in backend/.env!"
    )

INTAKE_API_KEY = os.getenv("INTAKE_API_KEY")
if not INTAKE_API_KEY:
    print("WARNING: INTAKE_API_KEY is not defined. Only admin tokens will be able to access intake routes.")

# ── Legacy session-token auth (for developer bootstrap / dashboard toggle) ─────
active_admin_sessions: set = set()
admin_token_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)
intake_key_header = APIKeyHeader(name="X-Intake-Api-Key", auto_error=False)


def verify_admin_token(token: str = Depends(admin_token_header)):
    """Validate legacy admin session token (used for developer bootstrap approval)."""
    if not token or token not in active_admin_sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid X-Admin-Token header required.",
        )
    return token


def verify_intake_or_admin(
    admin_token: str = Depends(admin_token_header),
    intake_key: str = Depends(intake_key_header),
    # Also accept JWT-authenticated users (citizen or admin)
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Accepts any of: legacy admin session token, intake API key, or valid JWT user.
    Used for classify and transcribe endpoints.
    """
    if admin_token and admin_token in active_admin_sessions:
        return "legacy_admin"
    if intake_key and INTAKE_API_KEY and intake_key == INTAKE_API_KEY:
        return "intake"
    if current_user is not None:
        return f"jwt_{current_user.role}"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Login required or provide a valid API key.",
    )


class VerifyPasswordRequest(BaseModel):
    password: str


# ── Upload directory for admin verification docs ───────────────────────────────
UPLOADS_DIR = os.path.join(root_dir, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


# ── App lifespan (DB init + seeding) ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup database table creation and seeding."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
    yield


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CivicVoice AI API",
    description="Backend API for CivicVoice AI (SDG 11 - Sustainable Cities & Settlements)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# ROOT
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def read_root():
    return {"message": "Welcome to CivicVoice AI API v2. Visit /docs for documentation."}


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY ADMIN SESSION (developer bootstrap — kept for first-admin approval)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/verify-password")
def verify_password_endpoint(payload: VerifyPasswordRequest):
    """
    Developer bootstrap endpoint. Use the ADMIN_PASSWORD from .env to get a
    session token, which can then be used to approve the first pending admin account.
    """
    if payload.password == ADMIN_PASSWORD:
        session_token = secrets.token_hex(16)
        active_admin_sessions.add(session_token)
        return {"status": "success", "token": session_token}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")


@app.get("/verify-token")
def verify_token_endpoint(token: str = Depends(verify_admin_token)):
    return {"status": "valid"}


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — REGISTRATION & LOGIN
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_citizen(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new citizen account.
    Validates that the ward exists and the email is not already taken.
    """
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    ward = db.query(Ward).filter(Ward.id == user_in.ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward ID {user_in.ward_id} not found.")

    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        hashed_password=hash_password(user_in.password),
        role="citizen",
        ward_id=user_in.ward_id,
        locality_description=user_in.locality_description,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/register/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_admin_applicant(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    password: str = Form(...),
    ward_id: int = Form(...),
    locality_description: str = Form(None),
    verification_doc: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Register an admin applicant. Account created as 'admin_pending'.
    The uploaded verification document (municipal ID, appointment letter, etc.)
    is stored on the server and reviewed by an approved admin before activation.
    """
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward ID {ward_id} not found.")

    # Save uploaded document
    safe_name = f"admin_doc_{secrets.token_hex(8)}_{verification_doc.filename}"
    doc_path = os.path.join(UPLOADS_DIR, safe_name)
    with open(doc_path, "wb") as f:
        shutil.copyfileobj(verification_doc.file, f)

    user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        role="admin_pending",
        ward_id=ward_id,
        locality_description=locality_description,
        admin_doc_filename=safe_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user (citizen, admin_pending, or admin).
    Returns a JWT access token and role for frontend routing.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_pw(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        ward_id=user.ward_id,
        full_name=user.full_name,
    )


@app.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


# ══════════════════════════════════════════════════════════════════════════════
# AUTH — ADMIN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/auth/admin/pending", response_model=List[AdminPendingResponse])
def list_pending_admins(
    db: Session = Depends(get_db),
    # Accept either a JWT admin OR a legacy developer session token
    admin_token: str = Depends(admin_token_header),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List all admin_pending accounts. Accessible by:
    - An approved admin (JWT)
    - The developer (legacy ADMIN_PASSWORD session token)
    """
    is_legacy = admin_token and admin_token in active_admin_sessions
    is_jwt_admin = current_user and current_user.role == "admin"
    if not is_legacy and not is_jwt_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return db.query(User).filter(User.role == "admin_pending").all()


@app.patch("/auth/admin/approve/{user_id}", response_model=UserResponse)
def approve_or_reject_admin(
    user_id: int,
    body: AdminApproveRequest,
    db: Session = Depends(get_db),
    admin_token: str = Depends(admin_token_header),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Approve or reject a pending admin application.
    Accessible by an approved admin (JWT) or the developer (legacy session token).

    action = "approve" → sets role to "admin"
    action = "reject"  → sets role to "rejected", stores rejection_reason
    """
    is_legacy = admin_token and admin_token in active_admin_sessions
    is_jwt_admin = current_user and current_user.role == "admin"
    if not is_legacy and not is_jwt_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    pending_user = db.query(User).filter(User.id == user_id).first()
    if not pending_user:
        raise HTTPException(status_code=404, detail="User not found.")
    if pending_user.role not in ("admin_pending",):
        raise HTTPException(status_code=400, detail="User is not in pending_admin state.")

    if body.action == "approve":
        pending_user.role = "admin"
        pending_user.rejection_reason = None
    elif body.action == "reject":
        pending_user.role = "rejected"
        pending_user.rejection_reason = body.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'.")

    db.commit()
    db.refresh(pending_user)
    return pending_user


# ══════════════════════════════════════════════════════════════════════════════
# WARDS & DEPARTMENTS (public)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/wards", response_model=List[WardResponse])
def get_wards(db: Session = Depends(get_db)):
    """Retrieve all administrative wards."""
    return db.query(Ward).all()


@app.get("/departments", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    """Retrieve all municipal departments."""
    return db.query(Department).all()


# ══════════════════════════════════════════════════════════════════════════════
# COMPLAINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/complaints", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db),
    auth_mode: str = Depends(verify_intake_or_admin),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Submit a new civic complaint.
    Verifies ward and department exist, persists the complaint,
    and creates the initial status history entry.
    """
    ward = db.query(Ward).filter(Ward.id == complaint_in.ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward with ID {complaint_in.ward_id} not found.")

    dept = db.query(Department).filter(Department.id == complaint_in.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department with ID {complaint_in.department_id} not found.")

    status_val = "manual_review" if complaint_in.transcription_success is False else "pending"
    notes_val = (
        "Audio transcription failed. Complaint queued for human review."
        if status_val == "manual_review"
        else "Complaint successfully registered."
    )

    # Resolve user_id: prefer explicit field, fall back to JWT user
    resolved_user_id = complaint_in.user_id
    if resolved_user_id is None and current_user is not None:
        resolved_user_id = current_user.id

    db_complaint = Complaint(
        raw_input=complaint_in.raw_input,
        original_transcription=complaint_in.original_transcription,
        originalLanguage=complaint_in.originalLanguage,
        complaintType=complaint_in.complaintType,
        translatedText=complaint_in.translatedText,
        mediaAttachments=complaint_in.mediaAttachments,
        urgency_score=complaint_in.urgency_score,
        classification_method=complaint_in.classification_method,
        location_description=complaint_in.location_description,
        ward_id=complaint_in.ward_id,
        department_id=complaint_in.department_id,
        user_id=resolved_user_id,
        status=status_val,
    )
    db.add(db_complaint)
    db.flush()

    initial_history = StatusHistory(
        complaint_id=db_complaint.id,
        status=status_val,
        notes=notes_val,
    )
    db.add(initial_history)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


@app.post("/complaints/upload")
async def upload_complaint_media(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Securely upload an image or video attachment for a complaint.
    Validates file size (max 10MB) and content type (images and videos only).
    """
    content_type = file.content_type or ""
    if not content_type.startswith("image/") and not content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only images and videos are supported."
        )

    # Validate size (max 10MB)
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size allowed is 10MB."
        )

    type_group = "image" if content_type.startswith("image/") else "video"
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext:
        file_ext = ".jpg" if type_group == "image" else ".mp4"

    safe_name = f"media_{secrets.token_hex(16)}{file_ext}"
    doc_path = os.path.join(UPLOADS_DIR, safe_name)

    try:
        with open(doc_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    base_url = str(request.base_url).rstrip("/")
    url = f"{base_url}/uploads/{safe_name}"

    return {"url": url, "type": type_group}


@app.post("/complaints/social-draft", response_model=SocialDraftResponse)
def get_social_post_draft(
    request: SocialDraftRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate an X-length social media post draft from a complaint's details.
    Accessible by authenticated citizens.
    """
    from .agent.llm_client import generate_social_post_draft
    draft = generate_social_post_draft(
        text=request.text,
        category=request.category,
        location=request.location,
        has_media=request.has_media
    )
    return {"draft": draft}


@app.get("/complaints", response_model=List[ComplaintResponse])
def list_complaints(
    ward_id: Optional[int] = Query(None, description="Filter by Ward ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
):
    """List all complaints with optional ward/status filters. Public endpoint."""
    query = db.query(Complaint)
    if ward_id is not None:
        query = query.filter(Complaint.ward_id == ward_id)
    if status_filter is not None:
        query = query.filter(Complaint.status == status_filter)
    return query.order_by(Complaint.timestamp.desc()).all()


@app.get("/complaints/my", response_model=List[ComplaintResponse])
def list_my_complaints(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return complaints filed by the currently authenticated citizen,
    plus all complaints from their ward (even those filed by others).
    Citizens see the full accountability picture for their locality.
    """
    if current_user.ward_id is None:
        return []
    return (
        db.query(Complaint)
        .filter(Complaint.ward_id == current_user.ward_id)
        .order_by(Complaint.timestamp.desc())
        .all()
    )


@app.get("/complaints/stats", response_model=ComplaintStatsResponse)
def get_complaint_stats(
    scope: str = Query("my", description="Scope: 'my', 'all', or 'specific'"),
    ward_id: Optional[int] = Query(None, description="Ward ID if scope is specific"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Retrieve counts for complaint statistics banner based on scope.
    Resolves 'my' scope via JWT current_user.ward_id and ignores client ward_id.
    """
    target_ward_id = None
    
    if scope == "my":
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication token required for 'my' scope.")
        target_ward_id = current_user.ward_id
    elif scope == "specific":
        target_ward_id = ward_id
    # If scope is 'all', target_ward_id remains None and no filter is applied

    query = db.query(Complaint)
    if scope != "all" and target_ward_id is not None:
        query = query.filter(Complaint.ward_id == target_ward_id)

    total = query.count()
    resolved = query.filter(Complaint.status == "resolved").count()
    active = total - resolved
    resolution_pct = round((resolved / total) * 100) if total > 0 else 0

    return {
        "total": total,
        "active": active,
        "resolved": resolved,
        "resolution_pct": resolution_pct
    }


@app.patch("/complaints/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    status_change: ComplaintUpdateStatus,
    db: Session = Depends(get_db),
    # Accept either legacy admin token or JWT admin
    admin_token: str = Depends(admin_token_header),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Update status of a complaint. Requires admin privileges —
    either a JWT admin account or the legacy developer session token.
    """
    is_legacy = admin_token and admin_token in active_admin_sessions
    is_jwt_admin = current_user and current_user.role == "admin"
    if not is_legacy and not is_jwt_admin:
        raise HTTPException(status_code=401, detail="Unauthorized: Valid X-Admin-Token header required.")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found.")

    old_status = complaint.status
    new_status = status_change.status.lower()
    complaint.status = new_status

    history_entry = StatusHistory(
        complaint_id=complaint.id,
        status=new_status,
        notes=status_change.notes or f"Status changed: '{old_status}' → '{new_status}'.",
    )
    db.add(history_entry)
    db.commit()
    db.refresh(complaint)
    return complaint


@app.get("/complaints/{complaint_id}/resolution-time")
def get_complaint_resolution_time(complaint_id: int, db: Session = Depends(get_db)):
    """Return dynamic resolution time calculation for a specific complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found.")
    seconds = complaint.resolution_time_seconds
    return {
        "complaint_id": complaint.id,
        "status": complaint.status,
        "resolution_time_seconds": seconds,
        "resolution_time_formatted": f"{seconds}s" if seconds is not None else "Not yet resolved",
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO TRANSCRIPTION & CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    auth_mode: str = Depends(verify_intake_or_admin),
):
    """
    Receive an audio file and use Gemini to detect language,
    transcribe, and translate to English.
    """
    try:
        file_bytes = await file.read()
        mime_type = file.content_type or "audio/mpeg"
        from .agent.llm_client import transcribe_and_translate_audio
        return transcribe_and_translate_audio(file_bytes, mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.post("/classify", response_model=ClassifyResponse)
def classify_complaint_endpoint(
    request: ClassifyRequest,
    db: Session = Depends(get_db),
    auth_mode: str = Depends(verify_intake_or_admin),
):
    """
    Run the LangGraph classification agent on a complaint description.
    Returns category, urgency score, department routing, and reasoning.
    Designed to be triggered by n8n or the admin intake dashboard.
    """
    ward = db.query(Ward).filter(Ward.id == request.ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail=f"Ward {request.ward_id} not found.")

    initial_state = {
        "raw_input": request.raw_input,
        "ward_id": request.ward_id,
        "complaintType": None,
        "urgency_score": None,
        "originalLanguage": request.originalLanguage,
        "translatedText": None,
        "mediaAttachments": None,
        "department_id": None,
        "department_name": None,
        "classification_method": None,
        "reasoning": None,
        "transcription_success": request.transcription_success,
        "error": None,
    }

    try:
        final_state = agent_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LangGraph execution failed: {str(e)}")

    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=f"LangGraph error: {final_state['error']}")

    return {
        "raw_input": request.raw_input,
        "ward_id": request.ward_id,
        "complaintType": final_state["complaintType"],
        "urgency_score": final_state["urgency_score"],
        "originalLanguage": final_state["originalLanguage"],
        "translatedText": final_state.get("translatedText") or request.raw_input,
        "department_id": final_state["department_id"],
        "department_name": final_state["department_name"],
        "classification_method": final_state.get("classification_method", "fallback"),
        "reasoning": final_state["reasoning"],
        "transcription_success": final_state.get("transcription_success", request.transcription_success),
    }


# ══════════════════════════════════════════════════════════════════════════════
# STATIC FILES
# ══════════════════════════════════════════════════════════════════════════════

test_audio_path = os.path.join(root_dir, "test_audio")
if os.path.exists(test_audio_path):
    app.mount("/test_audio", StaticFiles(directory=test_audio_path), name="static_test_audio")

uploads_path = UPLOADS_DIR
if os.path.exists(uploads_path):
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="static_uploads")
