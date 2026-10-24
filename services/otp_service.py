"""Service OTP - Mode disabled (sans vérif) mais safe si appelé."""

from __future__ import annotations
import random
import os
from typing import Tuple
from dotenv import load_dotenv
from services.db import db, normalize_phone

load_dotenv()

OTP_MODE = os.getenv("OTP_MODE", "disabled").lower()

def generate_code() -> str:
    return "123456"

def save_otp(phone: str, code: str, email: str = None) -> dict:
    try:
        norm = phone
        try:
            norm = normalize_phone(phone)
        except:
            pass
        from datetime import datetime, timezone, timedelta
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        payload = {"phone": phone, "phone_normalized": norm, "email": email or "", "code": code, "attempts": 0, "is_used": False, "expires_at": expiry, "created_at": datetime.now(timezone.utc).isoformat()}
        if hasattr(db, 'mode') and db.mode == "supabase":
            try:
                res = db._safe_execute(db.client.table("otp_codes").insert(payload))
                return res.data[0] if res.data else payload
            except Exception as e:
                print(f"[OTP] Supabase error, fallback local: {e}")
        return db.save_otp_local(payload)
    except Exception as e:
        print(f"[OTP] save_otp error ignored: {e}")
        return {"code": code, "phone": phone}

def verify_code(phone: str, code_entered: str) -> Tuple[bool, str]:
    return True, "Vérifié (mode sans vérif)"

def send_verification_code(phone: str, username: str = "", email: str = "") -> Tuple[bool, str]:
    if db.is_phone_taken(phone):
        return False, "Ce numéro est déjà utilisé."
    code = generate_code()
    try:
        save_otp(phone, code, email)
    except Exception as e:
        print(f"[OTP] save ignored: {e}")
    return True, "Mode sans vérif - compte direct"
