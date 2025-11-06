Project layout

tokenized-kyc/
├─ app/
│  ├─ main.py                # FastAPI application + routers
│  ├─ models.py              # SQLAlchemy models (Profile, Consent, Token, Audit)
│  ├─ db.py                  # DB session + init
│  ├─ ai.py                  # Generative-AI helpers (OCR, extraction, summarization)
│  ├─ utils.py               # signing, encryption stub
│  ├─ policy.py              # simple policy engine
│  └─ schemas.py             # Pydantic schemas
├─ requirements.txt
├─ Dockerfile
└─ README.md
# Tokenised KYC Reference

1. Install:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

2. Run:
   uvicorn app.main:app --reload --port 8000

3. Endpoints:
   POST /enrolments (multipart-file) -> create profile
   POST /consents (json) -> create consent
   POST /tokens (json) -> issue token
   GET /resolve/{token_id}?requester=<fi_id> -> resolve token
   POST /tokens/{token_id}/revoke -> revoke

4. Notes:
   - AI modules use pytesseract and transformer models; if not installed/downloaded they fallback to heuristics.
   - Replace sign_token with HSM-based signing for production.
   - Add OAuth2/mTLS for client auth.
