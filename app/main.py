# app/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from app.db import SessionLocal, init_db
from app import models, utils, ai, policy
from sqlalchemy.orm import Session
from app import schemas
import io

app = FastAPI(title="Tokenised KYC Service - Reference")

# Initialize DB
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Enrolment: upload KYC doc, run OCR/extract and create profile
@app.post("/enrolments", response_model=schemas.ProfileOut)
async def create_profile(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    # 1) OCR + extraction
    extracted = ai.do_ocr_and_extract(contents)
    name = extracted.get("canonical_name") or "Unknown"
    dob = extracted.get("dob")
    address = extracted.get("address") or ""
    # 2) store profile (address hashed)
    address_hash = utils.hash_value(address) if address else None
    profile = models.Profile(canonical_name=name, dob=dob, address_hash=address_hash, evidence_refs=[file.filename])
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # audit
    db.add(models.Audit(actor="system", action="create_profile", target=profile.profile_id))
    db.commit()

    return {
        "profile_id": profile.profile_id,
        "canonical_name": profile.canonical_name,
        "dob": profile.dob,
        "address_hash": profile.address_hash
    }

# --- Consent creation
@app.post("/consents", response_model=schemas.ConsentOut)
def create_consent(payload: schemas.ConsentIn, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.profile_id == payload.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    now = datetime.utcnow()
    expires = now + timedelta(days=payload.duration_days)
    consent_text = f"Consent to share {payload.scope} with {payload.granted_to} for {payload.purpose}"
    summary = ai.summarize_consent(consent_text)
    consent = models.Consent(profile_id=payload.profile_id, granted_to=payload.granted_to,
                             scope=payload.scope, purpose=payload.purpose,
                             granted_at=now, expires_at=expires, consent_text=summary)
    db.add(consent)
    db.commit()
    db.refresh(consent)
    db.add(models.Audit(actor=payload.profile_id, action="create_consent", target=consent.consent_id))
    db.commit()
    return {"consent_id": consent.consent_id}

# --- Issue token
@app.post("/tokens", response_model=schemas.TokenOut)
def issue_token(payload: schemas.TokenIn, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.profile_id == payload.profile_id).first()
    consent = db.query(models.Consent).filter(models.Consent.consent_id == payload.consent_id).first()
    if not profile or not consent:
        raise HTTPException(404, "profile or consent not found")
    if consent.profile_id != profile.profile_id:
        raise HTTPException(400, "consent does not belong to profile")
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(hours=payload.ttl_hours)
    token_payload = {
        "profile_id": profile.profile_id,
        "consent_id": consent.consent_id,
        "recipient": payload.recipient,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat()
    }
    signature = utils.sign_token(token_payload)
    token = models.Token(profile_id=profile.profile_id, recipient=payload.recipient,
                         issued_at=issued_at, expires_at=expires_at, signature=signature,
                         consent_id=consent.consent_id)
    db.add(token)
    db.commit()
    db.refresh(token)
    db.add(models.Audit(actor="issuer", action="issue_token", target=token.token_id))
    db.commit()
    return {"token_id": token.token_id, "expires_at": token.expires_at.isoformat(), "signature": token.signature}

# --- Resolve token (called by FI)
@app.get("/resolve/{token_id}")
def resolve_token(token_id: str, requester: str = Query(...), db: Session = Depends(get_db)):
    token = db.query(models.Token).filter(models.Token.token_id == token_id).first()
    if not token:
        raise HTTPException(404, "token not found")
    # quick expiry check
    if token.expires_at and token.expires_at < datetime.utcnow():
        raise HTTPException(410, "token expired")
    consent = db.query(models.Consent).filter(models.Consent.consent_id == token.consent_id).first()
    ok, reason = policy.evaluate_policy(token, consent, requester)
    db.add(models.Audit(actor=requester, action="resolve_token", target=token_id, ts=datetime.utcnow()))
    db.commit()
    if not ok:
        raise HTTPException(403, reason)
    profile = db.query(models.Profile).filter(models.Profile.profile_id == token.profile_id).first()
    # produce attribute response according to consent scope (demo returns hashed address only)
    resp = {"profile_id": profile.profile_id, "canonical_name": profile.canonical_name}
    if "address" in consent.scope:
        resp["address_hash"] = profile.address_hash
    if "dob" in consent.scope:
        resp["dob"] = profile.dob
    return resp

# --- Revoke token
@app.post("/tokens/{token_id}/revoke")
def revoke_token(token_id: str, db: Session = Depends(get_db)):
    token = db.query(models.Token).filter(models.Token.token_id == token_id).first()
    if not token:
        raise HTTPException(404, "token not found")
    token.status = "revoked"
    db.add(models.Audit(actor="system", action="revoke_token", target=token_id))
    db.commit()
    return JSONResponse({"ok": True})
