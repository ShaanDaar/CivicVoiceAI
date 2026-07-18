from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from .database import Base
import json
import os

PORTALS_DATA = {}
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    portals_path = os.path.join(current_dir, "portals.json")
    if os.path.exists(portals_path):
        with open(portals_path, "r", encoding="utf-8") as f:
            raw_portals = json.load(f)
            for item in raw_portals:
                key = (item["city"].lower().strip(), item["category"].lower().strip())
                PORTALS_DATA[key] = item
except Exception as e:
    print(f"Failed to load portals.json: {e}")

CATEGORY_MAP = {
    "Water": "Water & Sanitation",
    "Electricity": "Electricity & Power",
    "Roads": "Roads & Drainage",
    "Sanitation": "Waste Management",
    "Public Safety": "Public Safety",
    "Other": "Other"
}


class User(Base):
    """
    Represents a registered user — either a citizen or a municipal admin.
    - Citizens can file complaints for their ward.
    - Admins can triage/resolve all complaints and approve pending admin accounts.
    - admin_pending: submitted doc, waiting for approval from an existing admin.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

    # Role: "citizen" | "admin" | "admin_pending"
    role = Column(String, default="citizen", nullable=False)

    # Locality — which ward this user belongs to
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=True)
    locality_description = Column(String, nullable=True)  # freeform address

    # Admin verification — filename of uploaded document (stored in uploads/)
    admin_doc_filename = Column(String, nullable=True)
    # Optional rejection reason set by approving admin
    rejection_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    ward = relationship("Ward")
    complaints = relationship("Complaint", back_populates="submitter", foreign_keys="Complaint.user_id")


class Ward(Base):
    """
    Represents an informal settlement or municipal administrative ward.
    """
    __tablename__ = "wards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    city = Column(String, default="Mumbai", nullable=False)

    # Relationships
    complaints = relationship("Complaint", back_populates="ward")


class Department(Base):
    """
    Represents a municipal department (e.g., Water, Electricity) handling complaints.
    """
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    # Relationships
    complaints = relationship("Complaint", back_populates="department")


class Complaint(Base):
    """
    Represents a citizen-submitted complaint.
    Stores metadata on routing, language detection, urgency, and location detail.
    """
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    raw_input = Column(Text, nullable=False)
    original_transcription = Column(Text, nullable=True)
    originalLanguage = Column(String, nullable=True)
    complaintType = Column(String, nullable=True)
    translatedText = Column(Text, nullable=True)
    mediaAttachments = Column(JSON, nullable=True)
    urgency_score = Column(Integer, nullable=True)
    location_description = Column(String, nullable=True)
    
    ward_id = Column(Integer, ForeignKey("wards.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    # Optional: which registered user submitted this complaint (null for seeded/admin-simulated)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, in-progress, resolved, manual_review, etc.
    classification_method = Column(String, default="fallback", nullable=True) # llm or fallback
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    ward = relationship("Ward", back_populates="complaints")
    department = relationship("Department", back_populates="complaints")
    submitter = relationship("User", back_populates="complaints", foreign_keys=[user_id])
    status_history = relationship("StatusHistory", back_populates="complaint", cascade="all, delete-orphan", lazy="joined")

    @property
    def department_name(self) -> str | None:
        """Helper to return parent department name directly."""
        return self.department.name if self.department else None

    @property
    def ward_name(self) -> str | None:
        """Helper to return parent ward name directly."""
        return self.ward.name if self.ward else None

    @property
    def resolution_time_seconds(self) -> int | None:
        """
        Dynamically calculates resolution time in seconds by comparing the earliest
        status history entry where status is 'pending' or 'manual_review' (or falling back to complaint creation timestamp)
        and the status history entry where status is 'resolved'.
        Returns None if the complaint is not currently resolved.
        """
        if self.status != "resolved":
            return None

        # Gather and sort all status history timestamps
        history_list = sorted(self.status_history, key=lambda h: h.timestamp)
        
        pending_time = None
        resolved_time = None

        for record in history_list:
            if record.status in ["pending", "manual_review"] and pending_time is None:
                pending_time = record.timestamp
            elif record.status == "resolved" and resolved_time is None:
                # Get the first transition to resolved status
                resolved_time = record.timestamp

        # Fallback to complaint creation timestamp if 'pending' history doesn't exist
        start_time = pending_time if pending_time is not None else self.timestamp
        end_time = resolved_time

        if start_time and end_time:
            # Both Datetimes should be offset-naive (or offset-aware). In Python/SQLite they default to naïve.
            # Make sure we avoid "tz-aware vs tz-naive" subtraction issues.
            # We strip tzinfos if they differ just in case, but usually they are naive datetimes.
            if start_time.tzinfo != end_time.tzinfo:
                start_time = start_time.replace(tzinfo=None)
                end_time = end_time.replace(tzinfo=None)
            
            diff = (end_time - start_time).total_seconds()
            return int(diff) if diff >= 0 else 0
        
        return None

    def _get_portal_info(self) -> dict | None:
        if not self.ward or not self.complaintType:
            return None
        city_name = getattr(self.ward, "city", "Mumbai") or "Mumbai"
        city_key = city_name.lower().strip()
        category_name = CATEGORY_MAP.get(self.complaintType, "Other")
        category_key = category_name.lower().strip()
        return PORTALS_DATA.get((city_key, category_key))

    @property
    def portal_name(self) -> str | None:
        info = self._get_portal_info()
        return info["portal_name"] if info else None

    @property
    def portal_url(self) -> str | None:
        info = self._get_portal_info()
        return info["portal_url"] if info else None

    @property
    def portal_status(self) -> str | None:
        info = self._get_portal_info()
        return info["status"] if info else None

    @property
    def portal_citation(self) -> str | None:
        info = self._get_portal_info()
        return info["citation"] if info else None


class StatusHistory(Base):
    """
    Tracks state transitions of complaints to calculate resolution times and show audit trail.
    """
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    complaint = relationship("Complaint", back_populates="status_history")
