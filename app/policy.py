# app/policy.py
from datetime import datetime

def evaluate_policy(token_record, consent_record, requester):
    """
    Simple PDP: checks token active, consent not revoked/expired, requester matches recipient.
    In real life, call a PDP (OPA, custom engine) and apply attribute-level transformation rules.
    """
    if token_record.status != "active":
        return False, "token_not_active"
    if token_record.recipient != requester:
        return False, "recipient_mismatch"
    if consent_record.revoked_at:
        return False, "consent_revoked"
    if consent_record.expires_at and consent_record.expires_at < datetime.utcnow():
        return False, "consent_expired"
    return True, "ok"
