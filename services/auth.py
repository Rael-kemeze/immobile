"""Session utilisateur - avec login/register + change_password + delete_account."""

from __future__ import annotations
from typing import Optional, Dict, Any, Tuple
from services.db import db, hash_password, normalize_phone
from services.config import APP_CONFIG

class Session:
    """Session globale de l'utilisateur connecté."""
    user: Optional[Dict[str, Any]] = None
    
    @classmethod
    def is_logged(cls) -> bool:
        return cls.user is not None
    
    @classmethod
    def is_admin(cls) -> bool:
        if not cls.user:
            return False
        return cls.user.get("role") in ("SUPER_ADMIN", "ADMIN", "ADMIN_CITY", "ADMIN_ZONE")
    
    @classmethod
    def logout(cls):
        cls.user = None

    @classmethod
    def login(cls, phone: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not phone or not password:
            return None, "Remplis tous les champs"
        if not normalize_phone(phone):
            return None, "Numéro invalide"
        user = db.authenticate(phone, password)
        if not user:
            return None, "Numéro ou mot de passe incorrect"
        if user.get("is_blocked"):
            return None, "Compte bloqué - contacte l'admin"
        cls.user = user
        return user, None

    @classmethod
    def register(cls, username: str, phone: str, password: str, confirm_password: str, 
                 country_code: str, city: str, locality: str, email: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not username or len(username.strip()) < 3:
            return None, "Nom trop court (min 3 caractères)"
        if not phone or len(normalize_phone(phone)) < 9:
            return None, "Numéro invalide"
        if not password or len(password) < 4:
            return None, "Mot de passe trop court (min 4)"
        if password != confirm_password:
            return None, "Les mots de passe ne correspondent pas"
        if not city or not locality:
            return None, "Ville et quartier requis"
        if db.is_phone_taken(phone):
            return None, "Ce numéro est déjà utilisé"
        if db.get_user_by_username(username.strip()):
            return None, "Ce nom d'utilisateur est déjà pris"
        try:
            user = db.create_user(
                username=username.strip(),
                phone=phone.strip(),
                password=password,
                city=city.strip(),
                locality=locality.strip(),
                email=email,
                country_code=country_code or APP_CONFIG.get("DEFAULT_COUNTRY_CODE", "CM")
            )
            cls.user = user
            return user, None
        except ValueError as ve:
            if "PHONE_ALREADY_TAKEN" in str(ve):
                return None, "Ce numéro est déjà utilisé"
            return None, f"Erreur: {ve}"
        except Exception as ex:
            return None, f"Erreur création compte: {ex}"

    @classmethod
    def change_password(cls, current: str, new: str, confirm: str) -> Tuple[bool, Optional[str]]:
        """Change mot de passe - utilisé dans settings et widgets."""
        if not cls.user:
            return False, "Non connecté"
        if not current or not new or not confirm:
            return False, "Remplis tous les champs"
        if new != confirm:
            return False, "Les nouveaux mots de passe ne correspondent pas"
        if len(new) < 4:
            return False, "Nouveau mot de passe trop court"
        
        # Vérifie ancien mot de passe
        if cls.user.get("password_hash") != hash_password(current):
            return False, "Mot de passe actuel incorrect"
        
        try:
            db.update_user(cls.user["id"], {"password_hash": hash_password(new)})
            cls.user["password_hash"] = hash_password(new)
            return True, None
        except Exception as ex:
            return False, f"Erreur: {ex}"

    @classmethod
    def delete_account(cls, password: str) -> Tuple[bool, Optional[str]]:
        """Suppression définitive du compte."""
        if not cls.user:
            return False, "Non connecté"
        if not password:
            return False, "Mot de passe requis"
        
        # Vérifie mot de passe
        if cls.user.get("password_hash") != hash_password(password):
            return False, "Mot de passe incorrect"
        
        try:
            user_id = cls.user["id"]
            db.delete_user(user_id)
            cls.user = None
            return True, None
        except Exception as ex:
            return False, f"Erreur suppression: {ex}"

    @classmethod
    def update_profile(cls, patch: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Mise à jour profil."""
        if not cls.user:
            return False, "Non connecté"
        try:
            db.update_user(cls.user["id"], patch)
            cls.user.update(patch)
            return True, None
        except ValueError as ve:
            if "PHONE_ALREADY_TAKEN" in str(ve):
                return False, "Ce numéro est déjà utilisé"
            return False, str(ve)
        except Exception as ex:
            return False, f"Erreur: {ex}"
