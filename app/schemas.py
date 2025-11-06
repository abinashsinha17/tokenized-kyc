# app/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class ProfileIn(BaseModel):
    canonical_name: str
    dob: Optional[str] = None
    address: str

class ProfileOut(BaseModel):
    profile_id: str
    canonical_name: str
    dob: Optional[str] = None
    address_hash: Optional[str] = None

class ConsentIn(BaseModel):
    profile_id: str
    granted_to: str
    scope: List[str]
    duration_days: int
    purpose: Optional[str] = None

class ConsentOut(BaseModel):
    consent_id: str

class TokenIn(BaseModel):
    profile_id: str
    consent_id: str
    recipient: str
    ttl_hours: int = 24

class TokenOut(BaseModel):
    token_id: str
    expires_at: str
    signature: str
