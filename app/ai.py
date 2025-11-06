# app/ai.py
"""
AI helpers. Two main roles:
 - do_ocr_and_extract(image_bytes): runs OCR -> text -> extract named entities
 - summarize_consent(text): create a plain language summary of consent text

This module tries to use pytesseract and transformers; if not available, falls back to simple heuristics.
"""
from typing import Dict, Any
from io import BytesIO
from PIL import Image
import pytesseract
import os

# For extraction via transformer NER (optional) - will download models on first run
try:
    from transformers import pipeline
    ner_pipe = pipeline("ner", grouped_entities=True)
    summarizer = pipeline("summarization")
except Exception:
    ner_pipe = None
    summarizer = None

def do_ocr(image_bytes: bytes) -> str:
    try:
        img = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        # fallback
        return image_bytes.decode("utf-8", errors="ignore")[:1000]

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    # Use transformer NER if available
    if ner_pipe:
        try:
            ents = ner_pipe(text[:2000])
            # Map common entities heuristically
            result = {}
            for e in ents:
                label = e.get("entity_group") or e.get("entity")
                word = e.get("word") or e.get("word")
                # basic mapping
                if "PER" in label or label.lower().startswith("person"):
                    result.setdefault("name", []).append(word)
                elif "LOC" in label or "address" in word.lower():
                    result.setdefault("address", []).append(word)
                elif "DATE" in label or any(tok.isdigit() for tok in word.split()):
                    result.setdefault("dates", []).append(word)
            # choose first if present
            return {
                "canonical_name": (result.get("name") or [None])[0],
                "address": " ".join(result.get("address") or []),
                "dob": (result.get("dates") or [None])[0],
                "raw": text
            }
        except Exception:
            pass
    # fallback heuristic extraction
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # naive heuristics: first non-empty line -> name; find line with 'DOB' or date-like -> dob
    name = lines[0] if lines else None
    dob = None
    address = None
    for l in lines[:10]:
        low = l.lower()
        if "dob" in low or "date of birth" in low or any(token.count("/") == 2 for token in l.split()):
            dob = l
        if any(word in low for word in ["street", "st.", "road", "rd", "lane", "addr", "city"]):
            if address:
                address += " " + l
            else:
                address = l
    return {"canonical_name": name, "address": address or "", "dob": dob, "raw": text}

def do_ocr_and_extract(image_bytes: bytes) -> Dict[str, Any]:
    text = do_ocr(image_bytes)
    return extract_entities_from_text(text)

def summarize_consent(consent_text: str) -> str:
    # Use summarizer if present (note: might download model)
    if summarizer:
        try:
            out = summarizer(consent_text, max_length=60, min_length=20, do_sample=False)
            return out[0]["summary_text"]
        except Exception:
            pass
    # fallback: naive first-sentence summary
    return (consent_text.split(".")[0] + ".") if consent_text else ""
