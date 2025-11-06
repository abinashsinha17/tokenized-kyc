# app/models.py
from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import relationship
import datetime
import uuid
from app.db import Base

def gen_uuid():
    return str(uuid.uuid4())

class Profile(Base):
    __tablename__ = "profiles"
    profile_id = Column(String, primary_key=True, default=gen_uuid)
    canonical_name = Column(String, nullable=False)
    dob = Column(String, nullable=True)
    address_hash = Column(String, nullable=True)
    evidence_refs = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    consents = relationship("Consent", back_populates="profile")
    tokens = relationship("Token", back_populates="profile")

class Consent(Base):
    __tablename__ = "consents"
    consent_id = Column(String, primary_key=True, default=gen_uuid)
    profile_id = Column(String, ForeignKey("profiles.profile_id"))
    granted_to = Column(String, nullable=False)
    scope = Column(JSON, default=[])  # list of attributes
    purpose = Column(String, nullable=True)
    granted_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    consent_text = Column(Text, nullable=True)

    profile = relationship("Profile", back_populates="consents")

class Token(Base):
    __tablename__ = "tokens"
    token_id = Column(String, primary_key=True, default=gen_uuid)
    profile_id = Column(String, ForeignKey("profiles.profile_id"))
    recipient = Column(String, nullable=False)
    issued_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    signature = Column(String, nullable=True)
    status = Column(String, default="active")
    consent_id = Column(String, ForeignKey("consents.consent_id"))

    profile = relationship("Profile", back_populates="tokens")

class Audit(Base):
    __tablename__ = "audit"
    event_id = Column(String, primary_key=True, default=gen_uuid)
    actor = Column(String)
    action = Column(String)
    target = Column(String)
    ts = Column(DateTime, default=datetime.datetime.utcnow)
    meta = Column(JSON, default={})
