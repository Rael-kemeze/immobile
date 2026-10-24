"""Service monétisation - Version avec Remote Config (active depuis admin UI sans republier APK)."""

from __future__ import annotations
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
import time
import os

# === SWITCH LOCAL (fallback si pas de Supabase) ===
ENABLE_MONETIZATION = False  # Sera overridé par remote config
ENABLE_BOOST_ONLY = False

PLANS = {
    "FREE": {"id": "FREE", "name": "Gratuit", "price": 0, "max_listings": 3, "max_photos": 3, "features": ["3 annonces gratuites", "Photos limitées"], "color": "#6B7280", "icon": "HOME_WORK_OUTLINED", "credits": 0},
    "BOOST": {"id": "BOOST", "name": "Boost", "price": 1000, "max_listings": 1, "max_photos": 10, "duration_days": 7, "features": ["En tête 7j", "Badge Sponsorisé", "10 photos", "Vues x5"], "color": "#F59E0B", "icon": "ROCKET_LAUNCH", "credits": 1},
    "PRO": {"id": "PRO", "name": "Pro Agence", "price": 5000, "max_listings": 999, "max_photos": 10, "duration_days": 30, "features": ["Illimité", "5 Boosts", "Badge PRO", "Support prio"], "color": "#0F6B3E", "icon": "VERIFIED", "credits": 5},
    "PREMIUM": {"id": "PREMIUM", "name": "Premium", "price": 15000, "max_listings": 999, "max_photos": 20, "duration_days": 30, "features": ["Tout Pro +", "20 photos", "Annonces Or", "Page agence"], "color": "#8B5CF6", "icon": "DIAMOND", "credits": 15},
}

MY_MTN_NUMBER = "6 81 84 76 66"
MY_ORANGE_NUMBER = "6 93 37 67 05"
MY_WHATSAPP = "6 93 37 67 05"

PAYMENT_METHODS = [
    {"id": "mtn", "name": "MTN MoMo", "icon": "📱", "number": MY_MTN_NUMBER, "color": "#FFCC00", "owner": "Rael Kemeze"},
    {"id": "orange", "name": "Orange Money", "icon": "🟠", "number": MY_ORANGE_NUMBER, "color": "#FF6600", "owner": "Rael Kemeze"},
    {"id": "manual", "name": "WhatsApp", "icon": "💬", "number": MY_WHATSAPP, "color": "#25D366", "owner": "WhatsApp"},
]

class Monetization:
    @staticmethod
    def _remote_enabled() -> Tuple[bool, bool, Dict[str, str]]:
        """Lit depuis remote config si dispo, sinon fallback local"""
        try:
            from services.remote_config import get_remote_config, is_monetization_enabled, is_boost_only, get_payment_numbers
            cfg = get_remote_config()
            enabled = is_monetization_enabled()
            boost_only = is_boost_only()
            numbers = get_payment_numbers()
            return enabled, boost_only, numbers
        except Exception as e:
            # Fallback .env local
            try:
                enabled = os.getenv("ENABLE_MONETIZATION", "false").lower() == "true" or ENABLE_MONETIZATION
                boost_only = os.getenv("ENABLE_BOOST_ONLY", "false").lower() == "true" or ENABLE_BOOST_ONLY
            except:
                enabled = ENABLE_MONETIZATION
                boost_only = ENABLE_BOOST_ONLY
            return enabled, boost_only, {"mtn": MY_MTN_NUMBER, "orange": MY_ORANGE_NUMBER, "whatsapp": MY_WHATSAPP}

    @staticmethod
    def is_enabled() -> bool:
        enabled, _, _ = Monetization._remote_enabled()
        return enabled

    @staticmethod
    def get_user_plan(user: Dict[str, Any]) -> Dict[str, Any]:
        plan_id = user.get("plan") or "FREE"
        plan = PLANS.get(plan_id, PLANS["FREE"])
        sub_until = user.get("subscription_until")
        if sub_until:
            try:
                if isinstance(sub_until, (int, float)):
                    exp = datetime.fromtimestamp(sub_until)
                else:
                    exp = datetime.fromisoformat(str(sub_until).replace("Z", ""))
                if datetime.now() > exp:
                    return PLANS["FREE"]
            except:
                pass
        return plan

    @staticmethod
    def get_credits(user: Dict[str, Any]) -> int:
        return int(user.get("credits") or 0)

    @staticmethod
    def get_free_remaining(user: Dict[str, Any], total_biens: int) -> int:
        plan = Monetization.get_user_plan(user)
        if plan["id"] in ("PRO", "PREMIUM"):
            return 999
        return max(0, PLANS["FREE"]["max_listings"] - total_biens)

    @staticmethod
    def can_publish(user: Dict[str, Any], total_biens: int) -> Tuple[bool, str]:
        enabled, boost_only, _ = Monetization._remote_enabled()
        if not enabled:
            return True, ""
        if boost_only:
            return True, ""
        plan = Monetization.get_user_plan(user)
        if plan["id"] in ("PRO", "PREMIUM"):
            return True, ""
        remaining = Monetization.get_free_remaining(user, total_biens)
        if remaining > 0:
            return True, ""
        return False, f"Limite gratuite atteinte ({PLANS['FREE']['max_listings']} annonces). Passe PRO ou Boost."

    @staticmethod
    def can_boost(user: Dict[str, Any]) -> Tuple[bool, str]:
        enabled, _, _ = Monetization._remote_enabled()
        if not enabled:
            return True, ""
        credits = Monetization.get_credits(user)
        if credits > 0:
            return True, ""
        return False, "Plus de crédits Boost. Achète un pack."

    @staticmethod
    def is_featured(bien: Dict[str, Any]) -> bool:
        if not bien.get("is_featured"):
            return False
        until = bien.get("featured_until")
        if not until:
            return False
        try:
            if isinstance(until, (int, float)):
                exp = datetime.fromtimestamp(until)
            else:
                exp = datetime.fromisoformat(str(until).replace("Z", ""))
            return datetime.now() < exp
        except:
            return False

    @staticmethod
    def boost_bien(bien: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
        until = datetime.now() + timedelta(days=days)
        bien["is_featured"] = True
        bien["featured_until"] = until.isoformat()
        bien["boosted_at"] = datetime.now().isoformat()
        return bien

    @staticmethod
    def apply_plan_to_user(user: Dict[str, Any], plan_id: str, db_instance=None) -> Dict[str, Any]:
        plan = PLANS.get(plan_id)
        if not plan:
            return user
        now = datetime.now()
        until = now + timedelta(days=plan.get("duration_days", 30))
        patch = {
            "plan": plan_id,
            "credits": (user.get("credits") or 0) + plan.get("credits", 0),
            "subscription_until": until.isoformat(),
            "is_pro": plan_id in ("PRO", "PREMIUM"),
            "is_premium": plan_id == "PREMIUM",
        }
        if db_instance:
            try:
                db_instance.update_user(user["id"], patch)
            except Exception as ex:
                print(f"[MONETIZE] Erreur: {ex}")
        user.update(patch)
        return user

    @staticmethod
    def sort_biens_by_monetization(biens: list) -> list:
        featured = [b for b in biens if Monetization.is_featured(b)]
        others = [b for b in biens if not Monetization.is_featured(b)]
        try:
            featured.sort(key=lambda x: x.get("created_at",""), reverse=True)
            others.sort(key=lambda x: x.get("created_at",""), reverse=True)
        except:
            pass
        return featured + others

    @staticmethod
    def get_payment_methods() -> list:
        """Retourne méthodes avec numéros à jour depuis remote config"""
        _, _, numbers = Monetization._remote_enabled()
        return [
            {"id": "mtn", "name": "MTN MoMo", "icon": "📱", "number": numbers.get("mtn", MY_MTN_NUMBER), "color": "#FFCC00", "owner": "Rael"},
            {"id": "orange", "name": "Orange Money", "icon": "🟠", "number": numbers.get("orange", MY_ORANGE_NUMBER), "color": "#FF6600", "owner": "Rael"},
            {"id": "manual", "name": "WhatsApp", "icon": "💬", "number": numbers.get("whatsapp", MY_WHATSAPP), "color": "#25D366", "owner": "WhatsApp"},
        ]

monetization = Monetization()
