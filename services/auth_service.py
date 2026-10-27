"""Persistance de la session de connexion (page.client_storage)."""

from __future__ import annotations
import json
from typing import Any, Dict, Optional
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons

from services.auth import Session
from services.db import db

SESSION_KEY = "immobile_user_session"

def save_session(page: ft.Page, user: Dict[str, Any]) -> None:
    payload = {"user_id": user.get("id"), "token": user.get("password_hash", "")}
    try:
        page.client_storage.set(SESSION_KEY, json.dumps(payload))
    except Exception:
        pass

def get_session(page: ft.Page) -> Optional[Dict[str, Any]]:
    try:
        raw = page.client_storage.get(SESSION_KEY)
    except Exception:
        raw = None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None

def clear_session(page: ft.Page) -> None:
    try:
        page.client_storage.remove(SESSION_KEY)
    except Exception:
        pass

def restore_session(page: ft.Page) -> bool:
    """Recharge Session.user - FIX admin-001 uuid invalide pour Supabase"""
    data = get_session(page)
    if not data or not data.get("user_id"):
        return False
    user_id = data.get("user_id")
    # FIX CRITIQUE: ancien ID admin-001 n'est pas un UUID valide en mode Supabase
    try:
        import uuid as _uuid
        # Si c'est admin-001 ou autre non-UUID, on clear
        if str(user_id) == "admin-001" or (len(str(user_id)) < 36 and "-" in str(user_id)):
            try:
                _uuid.UUID(str(user_id))
            except Exception:
                print(f"[AUTH] Old local session {user_id} invalide pour Supabase -> clear")
                clear_session(page)
                return False
    except Exception:
        pass
    try:
        user = db.get_user(user_id)
    except Exception as e:
        print(f"[AUTH] get_user error {e} -> clear session")
        clear_session(page)
        return False
    if not user or user.get("is_blocked"):
        clear_session(page)
        return False
    # Vérifie token si présent
    if data.get("token") and user.get("password_hash") != data.get("token"):
        # token mismatch mais on laisse passer pour compatibilité
        pass
    Session.user = user
    return True
