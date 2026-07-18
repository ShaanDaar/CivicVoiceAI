from datetime import datetime
from typing import Optional, List, Dict, Any
import enum
from pydantic import BaseModel, EmailStr

class ComplaintType(str, enum.Enum):
    Water = "Water"
    Sanitation = "Sanitation"
    Electricity = "Electricity"
    Roads = "Roads"
    PublicSafety = "Public Safety"
    Other = "Other"

class OriginalLanguage(str, enum.Enum):
    English = "English"
    Hindi = "Hindi"
    Kannada = "Kannada"
    Tamil = "Tamil"
    Telugu = "Telugu"
    Bengali = "Bengali"
    Marathi = "Marathi"
    Gujarati = "Gujarati"
    Urdu = "Urdu"
    Malayalam = "Malayalam"
    Punjabi = "Punjabi"
    Odia = "Odia"
    Unknown = "Unknown"


# --- WARD SCHEMAS ---
class WardBase(BaseModel):
    name: str
    description: str | None = None
    city: str = "Mumbai"

class WardCreate(WardBase):
    pass

class WardResponse(WardBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True


# --- DEPARTMENT SCHEMAS ---
class DepartmentBase(BaseModel):
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True


# --- STATUS HISTORY SCHEMAS ---
class StatusHistoryBase(BaseModel):
    status: str
    notes: str | None = None
    timestamp: datetime

class StatusHistoryCreate(BaseModel):
    status: str
    notes: str | None = None

class StatusHistoryResponse(StatusHistoryBase):
    id: int
    complaint_id: int

    class Config:
        orm_mode = True
        from_attributes = True


# --- COMPLAINT SCHEMAS ---
class ComplaintCreate(BaseModel):
    raw_input: str
    original_transcription: str | None = None
    originalLanguage: OriginalLanguage | None = OriginalLanguage.English
    complaintType: ComplaintType | None = ComplaintType.Other
    translatedText: str | None = None
    mediaAttachments: list[dict] | None = None
    urgency_score: int | None = None
    classification_method: str | None = None
    location_description: str | None = None
    ward_id: int
    department_id: int
    transcription_success: bool | None = True
    user_id: int | None = None  # Linked to the submitting citizen (optional)

class ComplaintUpdateStatus(BaseModel):
    status: str
    notes: str | None = None

class ComplaintResponse(BaseModel):
    id: int
    raw_input: str
    original_transcription: str | None = None
    originalLanguage: OriginalLanguage
    complaintType: ComplaintType
    translatedText: str | None = None
    mediaAttachments: list[dict] | None = None
    urgency_score: int | None = None
    classification_method: str | None = None
    location_description: str | None = None
    ward_id: int
    ward_name: str | None = None
    department_id: int
    department_name: str | None = None
    status: str
    timestamp: datetime
    user_id: int | None = None  # The citizen who filed it
    
    # Portal details
    portal_name: str | None = None
    portal_url: str | None = None
    portal_status: str | None = None
    portal_citation: str | None = None

    # Nested relations
    ward: WardResponse | None = None
    department: DepartmentResponse | None = None
    status_history: list[StatusHistoryResponse] = []
    
    # Dynamically calculated from sqlalchemy model property
    resolution_time_seconds: int | None = None

    class Config:
        orm_mode = True
        from_attributes = True


class ComplaintStatsResponse(BaseModel):
    total: int
    active: int
    resolved: int
    resolution_pct: int


class SocialDraftRequest(BaseModel):
    text: str
    category: str
    location: str
    has_media: bool = False


class SocialDraftResponse(BaseModel):
    draft: str


# --- CLASSIFY SCHEMAS ---
class ClassifyRequest(BaseModel):
    raw_input: str
    ward_id: int
    transcription_success: bool = True
    originalLanguage: OriginalLanguage | None = OriginalLanguage.English

class ClassifyResponse(BaseModel):
    raw_input: str
    ward_id: int
    complaintType: ComplaintType
    urgency_score: int
    originalLanguage: OriginalLanguage
    translatedText: str | None = None
    department_id: int
    department_name: str
    classification_method: str
    reasoning: str
    transcription_success: bool


# --- AUDIO SCHEMAS ---
class TranscribeResponse(BaseModel):
    original_transcription: str
    english_translation: str
    originalLanguage: OriginalLanguage
    transcription_success: bool


# --- USER / AUTH SCHEMAS ---

class UserCreate(BaseModel):
    """For citizen registration."""
    full_name: str
    email: str
    phone: str | None = None
    password: str
    ward_id: int
    locality_description: str | None = None

class UserResponse(BaseModel):
    """Safe user representation — no password."""
    id: int
    full_name: str
    email: str
    phone: str | None = None
    role: str
    ward_id: int | None = None
    locality_description: str | None = None
    admin_doc_filename: str | None = None
    rejection_reason: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    """Returned after successful login."""
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    ward_id: int | None = None
    full_name: str

class AdminPendingResponse(BaseModel):
    """List of pending admin applications visible to approved admins."""
    id: int
    full_name: str
    email: str
    phone: str | None = None
    ward_id: int | None = None
    locality_description: str | None = None
    admin_doc_filename: str | None = None
    created_at: datetime
    rejection_reason: str | None = None

    class Config:
        orm_mode = True
        from_attributes = True

class AdminApproveRequest(BaseModel):
    """Body for approving or rejecting a pending admin."""
    action: str  # "approve" | "reject"
    rejection_reason: str | None = None
