"""Couche d'acces aux donnees - FIX SUPABASE .env support."""

from __future__ import annotations
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# --- FIX: charge .env depuis racine projet + support .env.bak ---
_ROOT = Path(__file__).resolve().parent.parent
_ENV = _ROOT / ".env"
_ENV_BAK = _ROOT / ".env.bak"

# Si .env n'existe pas mais .env.bak existe (ton cas), on charge .env.bak
if not _ENV.exists() and _ENV_BAK.exists():
    print(f"[DB] .env introuvable -> chargement {_ENV_BAK}")
    load_dotenv(dotenv_path=_ENV_BAK, override=True)
else:
    load_dotenv(dotenv_path=_ENV, override=True)
    load_dotenv()  # fallback CWD

from .config import (
    APP_CONFIG,
    ROLE_SUPER_ADMIN,
    ROLE_USER,
    STATUS_APPROUVE,
    STATUS_EN_ATTENTE,
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "biens").strip()

# --- CLOUDINARY---
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "immobile").strip()  # dossier dans Cloudinary
USE_CLOUDINARY = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)

if USE_CLOUDINARY:
    print(f">>> [IMMOBILE] CLOUDINARY activé : {CLOUDINARY_CLOUD_NAME} (25 Go gratuit)")

# Debug - affiche mode au démarrage
if SUPABASE_URL and SUPABASE_KEY:
    mode_msg = f">>> [IMMOBILE] MODE SUPABASE : {SUPABASE_URL[:35]}..."
    if USE_CLOUDINARY:
        mode_msg += f" + CLOUDINARY {CLOUDINARY_FOLDER}"
    print(mode_msg)
else:
    print(">>> [IMMOBILE] MODE LOCAL activé -> local_db.json (SUPABASE_URL ou KEY manquant)")
    if _ENV.exists():
        print(f"  -> {_ENV} trouvé mais vide ou sans clés")
    if _ENV_BAK.exists():
        print(f"  -> {_ENV_BAK} existe - renomme le en .env !")

LOCAL_DB_PATH = Path(__file__).resolve().parent.parent / "local_db.json"
LOCAL_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "assets" / "uploads"
WEB_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ASSETS_DIR = LOCAL_UPLOAD_DIR.parent
MAX_IMAGE_SIDE = 1280

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def hash_password(password: str) -> str:
    return hashlib.sha256(("immobile$" + password).encode("utf-8")).hexdigest()

def new_id() -> str:
    return str(uuid.uuid4())

# ---------- FIX SECURITE TELEPHONE ----------
def normalize_phone(phone: str) -> str:
    """Normalise: +237 6 12 34 56 78 -> 612345678 (9 derniers chiffres)."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone).strip())
    if len(digits) >= 9:
        return digits[-9:]
    return digits

class Database:
    def __init__(self) -> None:
        self.client = None
        self.mode = "local"
        self.data = {"users": [], "biens": [], "favoris": [], "notifications": [], "user_alerts": [], "otp_codes": []}
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client
                from supabase.lib.client_options import ClientOptions
                options = ClientOptions(
                    auto_refresh_token=False,
                    persist_session=False,
                )
                self.client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
                self.mode = "supabase"
                print(f"[DB] Supabase client créé")
                # Charge aussi local comme fallback
                try:
                    self._load_local()
                except:
                    pass
            except Exception as exc:
                print(f"[DB] Supabase indisponible ({exc}), fallback local.")
                self.client = None
                self.mode = "local"
                self._load_local()
        else:
            self._load_local()

    def _safe_execute(self, query, retries=3):
        """Exécute une requête Supabase avec retry si Server disconnected"""
        import time
        last_err = None
        for i in range(retries):
            try:
                return query.execute()
            except Exception as e:
                msg = str(e).lower()
                last_err = e
                if "remoteprotocolerror" in msg or "server disconnected" in msg or "connection" in msg or "timeout" in msg:
                    wait = (i+1)*1.5
                    print(f"[DB] Retry {i+1}/{retries} après erreur réseau: {e} -> attente {wait}s")
                    time.sleep(wait)
                    # Recrée le client
                    try:
                        from supabase import create_client
                        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                    except:
                        pass
                    continue
                else:
                    raise
        print(f"[DB] Echec après {retries} tentatives: {last_err}")
        raise last_err


    def _load_local(self) -> None:
        if LOCAL_DB_PATH.exists():
            self.data = json.loads(LOCAL_DB_PATH.read_text(encoding="utf-8"))
        else:
            self.data = {"users": [], "biens": [], "favoris": [], "notifications": []}
            self._save_local()
        for key in ("users", "biens", "favoris", "notifications", "user_alerts", "otp_codes"):
            self.data.setdefault(key, [])

    def _save_local(self) -> None:
        LOCAL_DB_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- users ----------
    def get_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        norm_target = normalize_phone(phone)
        if not norm_target:
            return None
        if self.mode == "supabase":
            try:
                res = self._safe_execute(self.client.table("users").select("*").eq("phone", phone))
                if res.data:
                    return res.data[0]
                all_users = self.client.table("users").select("*").execute().data or []
                for u in all_users:
                    if normalize_phone(u.get("phone")) == norm_target:
                        return u
                return None
            except Exception as e:
                print(f"[DB] get_user_by_phone error: {e}")
                return None
        for u in self.data["users"]:
            if normalize_phone(u.get("phone") or "") == norm_target:
                return u
        return None

    def is_phone_taken(self, phone: str, exclude_user_id: Optional[str] = None) -> bool:
        norm_target = normalize_phone(phone)
        if not norm_target:
            return False
        if self.mode == "supabase":
            try:
                rows = self._safe_execute(self.client.table("users").select("id,phone")).data or []
                for u in rows:
                    if exclude_user_id and str(u.get("id")) == str(exclude_user_id):
                        continue
                    if normalize_phone(u.get("phone")) == norm_target:
                        return True
                return False
            except Exception as e:
                print(f"[DB] is_phone_taken error: {e}")
                return False
        for u in self.data["users"]:
            if exclude_user_id and str(u.get("id")) == str(exclude_user_id):
                continue
            if normalize_phone(u.get("phone") or "") == norm_target:
                return True
        return False

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        if self.mode == "supabase":
            res = self.client.table("users").select("*").eq("username", username).execute()
            return res.data[0] if res.data else None
        return next((u for u in self.data["users"] if u["username"] == username), None)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "supabase":
            # Fix: si ancien ID type admin-001, pas un UUID -> return None sans crasher
            try:
                import uuid as _uuid
                _uuid.UUID(str(user_id))
            except Exception:
                print(f"[DB] get_user skip invalid uuid: {user_id}")
                return None
            try:
                res = self.client.table("users").select("*").eq("id", user_id).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                print(f"[DB] get_user error {user_id}: {e}")
                return None
        return next((u for u in self.data["users"] if u["id"] == user_id), None)

    def list_users(self, search: str = "") -> List[Dict[str, Any]]:
        if self.mode == "supabase":
            q = self.client.table("users").select("*").order("created_at", desc=True)
            rows = q.execute().data or []
        else:
            rows = sorted(self.data["users"], key=lambda u: u.get("created_at", ""), reverse=True)
        if search:
            s = search.lower()
            rows = [u for u in rows if s in (u.get("username") or "").lower() or s in (u.get("phone") or "").lower() or s in (u.get("city") or "").lower()]
        return rows

    def create_user(self, username: str, phone: str, password: str, city: str, locality: str, profile_photo_url: Optional[str] = None, email: Optional[str] = None, country_code: Optional[str] = None) -> Dict[str, Any]:
        if self.is_phone_taken(phone):
            raise ValueError("PHONE_ALREADY_TAKEN: Ce numéro est déjà utilisé")
        role = ROLE_SUPER_ADMIN if normalize_phone(phone) == normalize_phone(APP_CONFIG["ADMIN_PHONE"]) else ROLE_USER
        payload = {"username": username, "phone": phone.strip(), "email": email, "password_hash": hash_password(password), "country_code": country_code or APP_CONFIG["DEFAULT_COUNTRY_CODE"], "city": city, "locality": locality, "profile_photo_url": profile_photo_url, "role": role, "is_blocked": False, "created_at": now_iso()}
        if self.mode == "supabase":
            res = self.client.table("users").insert(payload).execute()
            return res.data[0]
        payload["id"] = new_id()
        self.data["users"].append(payload)
        self._save_local()
        return payload

    def authenticate(self, phone: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_phone(phone)
        if not user:
            return None
        if user["password_hash"] != hash_password(password):
            return None
        if normalize_phone(phone) == normalize_phone(APP_CONFIG["ADMIN_PHONE"]) and user.get("role") != ROLE_SUPER_ADMIN:
            self.update_user(user["id"], {"role": ROLE_SUPER_ADMIN})
            user["role"] = ROLE_SUPER_ADMIN
        return user

    def update_user(self, user_id: str, patch: Dict[str, Any]) -> None:
        if "phone" in patch and patch["phone"]:
            if self.is_phone_taken(patch["phone"], exclude_user_id=user_id):
                raise ValueError("PHONE_ALREADY_TAKEN")
        if self.mode == "supabase":
            self.client.table("users").update(patch).eq("id", user_id).execute()
            return
        for u in self.data["users"]:
            if u["id"] == user_id:
                u.update(patch)
        self._save_local()

    def delete_user(self, user_id: str) -> None:
        if self.mode == "supabase":
            ids = [b["id"] for b in self.list_biens(only_active=False, user_id=user_id)]
            steps = [("favoris", "user_id", [user_id]), ("notifications", "user_id", [user_id]), ("user_alerts", "user_id", [user_id])]
            if ids:
                steps.append(("favoris", "bien_id", ids))
            steps += [("biens", "user_id", [user_id]), ("users", "id", [user_id])]
            for table, col, vals in steps:
                try:
                    self.client.table(table).delete().in_(col, vals).execute()
                except Exception as exc:
                    print(f"[DB] suppression {table} : {exc}")
            return
        mine = {b["id"] for b in self.data["biens"] if b["user_id"] == user_id}
        self.data["users"] = [u for u in self.data["users"] if u["id"] != user_id]
        self.data["biens"] = [b for b in self.data["biens"] if b["user_id"] != user_id]
        self.data["favoris"] = [f for f in self.data["favoris"] if f["user_id"] != user_id and f["bien_id"] not in mine]
        self.data["notifications"] = [n for n in self.data["notifications"] if n.get("user_id") != user_id]
        self.data["user_alerts"] = [a for a in self.data["user_alerts"] if a.get("user_id") != user_id]
        self._save_local()

    # ---------- OTP ----------
    def save_otp_local(self, payload: dict) -> dict:
        if not hasattr(self, 'data') or self.data is None:
            self.data = {"users": [], "biens": [], "favoris": [], "notifications": [], "user_alerts": [], "otp_codes": []}
        if "otp_codes" not in self.data:
            self.data["otp_codes"] = []
        payload["id"] = payload.get("id") or new_id()
        self.data["otp_codes"].append(payload)
        try:
            self._save_local()
        except Exception as e:
            print(f"[DB] _save_local error (ignored): {e}")
        return payload

    def get_latest_otp(self, phone: str) -> Optional[Dict[str, Any]]:
        norm = normalize_phone(phone)
        if self.mode == "supabase":
            try:
                res = self.client.table("otp_codes").select("*").eq("phone_normalized", norm).eq("is_used", False).order("created_at", desc=True).limit(1).execute()
                return res.data[0] if res.data else None
            except Exception as e:
                print(f"[OTP] get_latest_otp error: {e}")
        if "otp_codes" not in self.data:
            return None
        candidates = [o for o in self.data["otp_codes"] if o.get("phone_normalized") == norm and not o.get("is_used")]
        if not candidates:
            candidates = [o for o in self.data["otp_codes"] if normalize_phone(o.get("phone")) == norm and not o.get("is_used")]
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: x.get("created_at", ""), reverse=True)[0]

    def delete_expired_otps(self, phone: str):
        norm = normalize_phone(phone)
        if self.mode == "supabase":
            try:
                self.client.table("otp_codes").delete().eq("phone_normalized", norm).execute()
            except:
                pass
            return
        if "otp_codes" in self.data:
            self.data["otp_codes"] = [o for o in self.data["otp_codes"] if o.get("phone_normalized") != norm]
            self._save_local()

    def mark_otp_used(self, otp_id: str):
        if self.mode == "supabase":
            try:
                self.client.table("otp_codes").update({"is_used": True}).eq("id", otp_id).execute()
            except Exception as e:
                print(f"[OTP] mark used error: {e}")
            return
        for o in self.data.get("otp_codes", []):
            if o["id"] == otp_id:
                o["is_used"] = True
        self._save_local()

    def increment_otp_attempts(self, otp_id: str):
        if self.mode == "supabase":
            try:
                res = self.client.table("otp_codes").select("attempts").eq("id", otp_id).execute()
                if res.data:
                    cur = res.data[0].get("attempts", 0)
                    self.client.table("otp_codes").update({"attempts": cur+1}).eq("id", otp_id).execute()
            except:
                pass
            return
        for o in self.data.get("otp_codes", []):
            if o["id"] == otp_id:
                o["attempts"] = o.get("attempts", 0) + 1
        self._save_local()

    # ---------- biens, favoris etc. ----------
    def create_bien(self, payload: dict, force_approve: bool = False) -> dict:
        validation = APP_CONFIG["VALIDATION_OBLIGATOIRE"] and not force_approve
        payload = dict(payload)
        payload["status"] = STATUS_EN_ATTENTE if validation else STATUS_APPROUVE
        payload["is_active"] = not validation
        payload["created_at"] = now_iso()
        if self.mode == "supabase":
            optional_cols = ["salons", "cuisines", "nb_cuisines", "cuisine_interne", "cuisine_externe", "cuisine_type", "whatsapp2"]
            for attempt in range(8):
                try:
                    res = self._safe_execute(self.client.table("biens").insert(payload))
                    bien = res.data[0]
                    break
                except Exception as exc:
                    msg = str(exc).lower()
                    found = False
                    for col in optional_cols:
                        if col in msg and col in payload:
                            print(f"[DB] Colonne '{col}' absente, retry sans")
                            payload.pop(col, None)
                            found = True
                            break
                    if not found:
                        import re as _re
                        mm = _re.search(r"'(\w+)'", msg)
                        if mm:
                            cname = mm.group(1)
                            if cname in payload:
                                print(f"[DB] Colonne '{cname}' absente, retry sans")
                                payload.pop(cname, None)
                                found = True
                    if not found:
                        raise
        else:
            payload["id"] = new_id()
            self.data["biens"].append(payload)
            self._save_local()
            bien = payload
        if bien["is_active"]:
            self.notify_locality(bien)
        return bien


    def list_biens(self, search: str = "", type_bien: Optional[str] = None, transaction: Optional[str] = None, categorie: Optional[str] = None, city: Optional[str] = None, country_code: Optional[str] = None, prix_min: Optional[int] = None, prix_max: Optional[int] = None, prix_discutable: bool = False, only_active: bool = True, user_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mode == "supabase":
            q = self.client.table("biens").select("*")
            if only_active:
                q = q.eq("is_active", True)
            if user_id:
                q = q.eq("user_id", user_id)
            if status:
                q = q.eq("status", status)
            rows = q.order("created_at", desc=True).execute().data or []
        else:
            rows = sorted(self.data["biens"], key=lambda b: b.get("created_at", ""), reverse=True)
            if only_active:
                rows = [b for b in rows if b.get("is_active")]
            if user_id:
                rows = [b for b in rows if b.get("user_id") == user_id]
            if status:
                rows = [b for b in rows if b.get("status") == status]
        if search:
            s = search.lower()
            rows = [b for b in rows if s in (b.get("titre") or "").lower() or s in (b.get("city") or "").lower() or s in (b.get("locality") or "").lower()]
        if type_bien:
            rows = [b for b in rows if b.get("type_bien") == type_bien]
        if transaction:
            rows = [b for b in rows if b.get("transaction") == transaction]
        if categorie:
            rows = [b for b in rows if b.get("categorie") == categorie]
        if city:
            rows = [b for b in rows if b.get("city") == city]
        if country_code:
            rows = [b for b in rows if b.get("country_code") == country_code]
        if prix_min is not None:
            rows = [b for b in rows if (b.get("prix") or 0) >= prix_min]
        if prix_max is not None:
            rows = [b for b in rows if (b.get("prix") or 0) <= prix_max]
        if prix_discutable:
            rows = [b for b in rows if b.get("prix_discutable")]
        return rows

    def get_bien(self, bien_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "supabase":
            res = self.client.table("biens").select("*").eq("id", bien_id).execute()
            return res.data[0] if res.data else None
        return next((b for b in self.data["biens"] if b["id"] == bien_id), None)

    def approve_bien(self, bien_id: str) -> None:
        patch = {"is_active": True, "status": STATUS_APPROUVE}
        if self.mode == "supabase":
            self.client.table("biens").update(patch).eq("id", bien_id).execute()
        else:
            for b in self.data["biens"]:
                if b["id"] == bien_id:
                    b.update(patch)
            self._save_local()
        bien = self.get_bien(bien_id)
        if bien:
            self.notify_locality(bien)

    def update_bien(self, bien_id: str, patch: dict) -> dict:
        if self.mode == "supabase":
            optional_cols = ["salons", "cuisines", "nb_cuisines", "cuisine_interne", "cuisine_externe", "cuisine_type", "whatsapp2"]
            payload = dict(patch)
            for attempt in range(8):
                try:
                    res = self.client.table("biens").update(payload).eq("id", bien_id).execute()
                    return res.data[0] if res.data else {}
                except Exception as e:
                    msg = str(e).lower()
                    found = False
                    for col in optional_cols:
                        if col in msg and col in payload:
                            print(f"[DB] update_bien '{col}' absent, retry sans")
                            payload.pop(col, None)
                            found = True
                            break
                    if not found:
                        import re as _re
                        mm = _re.search(r"'([a-z0-9_]+)'", msg)
                        if mm and mm.group(1) in payload:
                            print(f"[DB] update_bien colonne '{mm.group(1)}' absente")
                            payload.pop(mm.group(1), None)
                            found = True
                    if not found:
                        print(f"[DB] update_bien erreur: {e}")
                        raise
            return {}
        else:
            for b in self.data["biens"]:
                if b["id"] == bien_id:
                    b.update(patch)
            self._save_local()
            return self.get_bien(bien_id) or {}





    def count_biens_of_user(self, user_id: str) -> int:
        return len(self.list_biens(only_active=False, user_id=user_id))

    def toggle_favori(self, user_id: str, bien_id: str) -> bool:
        if self.is_favori(user_id, bien_id):
            if self.mode == "supabase":
                self.client.table("favoris").delete().eq("user_id", user_id).eq("bien_id", bien_id).execute()
            else:
                self.data["favoris"] = [f for f in self.data["favoris"] if not (f["user_id"] == user_id and f["bien_id"] == bien_id)]
                self._save_local()
            return False
        row = {"user_id": user_id, "bien_id": bien_id}
        if self.mode == "supabase":
            self.client.table("favoris").insert(row).execute()
        else:
            self.data["favoris"].append(row)
            self._save_local()
        return True

    def is_favori(self, user_id: str, bien_id: str) -> bool:
        if self.mode == "supabase":
            res = self.client.table("favoris").select("bien_id").eq("user_id", user_id).eq("bien_id", bien_id).execute()
            return bool(res.data)
        return any(f["user_id"] == user_id and f["bien_id"] == bien_id for f in self.data["favoris"])

    def list_favoris(self, user_id: str) -> List[Dict[str, Any]]:
        if self.mode == "supabase":
            res = self.client.table("favoris").select("bien_id").eq("user_id", user_id).execute()
            ids = [r["bien_id"] for r in (res.data or [])]
        else:
            ids = [f["bien_id"] for f in self.data["favoris"] if f["user_id"] == user_id]
        biens = [self.get_bien(i) for i in ids]
        return [b for b in biens if b]

    def notify_locality(self, bien: Dict[str, Any]) -> None:
        message = f"Nouveau bien a {bien['city']} - {bien['locality']} : {bien['titre']}"
        if self.mode == "supabase":
            users = self.client.table("users").select("id").eq("city", bien["city"]).eq("locality", bien["locality"]).execute().data or []
        else:
            users = [{"id": u["id"]} for u in self.data["users"] if u["city"] == bien["city"] and u["locality"] == bien["locality"]]
        rows = [{"user_id": u["id"], "bien_id": bien["id"], "message": message, "is_read": False, "created_at": now_iso()} for u in users if u["id"] != bien.get("user_id")]
        if not rows:
            return
        if self.mode == "supabase":
            self.client.table("notifications").insert(rows).execute()
        else:
            for r in rows:
                r["id"] = new_id()
            self.data["notifications"].extend(rows)
            self._save_local()

    def list_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        if self.mode == "supabase":
            return self.client.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
        return sorted([n for n in self.data["notifications"] if n["user_id"] == user_id], key=lambda n: n.get("created_at", ""), reverse=True)

    def mark_notifications_read(self, user_id: str) -> None:
        if self.mode == "supabase":
            self.client.table("notifications").update({"is_read": True}).eq("user_id", user_id).execute()
            return
        for n in self.data["notifications"]:
            if n["user_id"] == user_id:
                n["is_read"] = True
        self._save_local()

    def create_alert(self, user_id: str, country: str, city: str, zone: str) -> Dict[str, Any]:
        row = {"user_id": user_id, "country": country, "city": city, "zone": zone, "created_at": now_iso()}
        if self.mode == "supabase":
            return self.client.table("user_alerts").insert(row).execute().data[0]
        row["id"] = new_id()
        self.data["user_alerts"].append(row)
        self._save_local()
        return row

    def list_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        if self.mode == "supabase":
            return self.client.table("user_alerts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data or []
        return sorted([a for a in self.data["user_alerts"] if a["user_id"] == user_id], key=lambda a: a.get("created_at", ""), reverse=True)

    def delete_alert(self, alert_id: str) -> None:
        if self.mode == "supabase":
            self.client.table("user_alerts").delete().eq("id", alert_id).execute()
            return
        self.data["user_alerts"] = [a for a in self.data["user_alerts"] if a["id"] != alert_id]
        self._save_local()

    @staticmethod
    def _prepare_image(file_path: str):
        raw = Path(file_path).read_bytes()
        suffix = Path(file_path).suffix.lower() or ".jpg"
        try:
            from PIL import Image, ImageOps
            with Image.open(io.BytesIO(raw)) as im:
                im = ImageOps.exif_transpose(im)
                if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                    im = im.convert("RGBA")
                    fond = Image.new("RGB", im.size, (255, 255, 255))
                    fond.paste(im, mask=im.split()[-1])
                    im = fond
                elif im.mode != "RGB":
                    im = im.convert("RGB")
                im.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=85, optimize=True)
                return buf.getvalue(), ".jpg"
        except ImportError:
            pass
        except Exception as exc:
            print(f"[PHOTO] redimensionnement impossible ({exc})")
        return raw, suffix

    def upload_photo_cloudinary(self, image_data: bytes, filename: str) -> str:
        """Upload vers Cloudinary (25 Go gratuit, illimité vs Supabase 1 Go)."""
        try:
            import cloudinary
            import cloudinary.uploader
            
            cloudinary.config(
                cloud_name=CLOUDINARY_CLOUD_NAME,
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                secure=True
            )
            
            # Upload avec optimisation automatique
            result = cloudinary.uploader.upload(
                image_data,
                public_id=f"{CLOUDINARY_FOLDER}/{filename.replace('.', '_')}",
                folder=CLOUDINARY_FOLDER,
                resource_type="image",
                overwrite=True,
                transformation=[
                    {"width": 1280, "height": 1280, "crop": "limit"},  # limite taille
                    {"quality": "auto:good"},  # qualité auto
                    {"fetch_format": "auto"}  # format auto (webp si possible)
                ]
            )
            
            url = result.get("secure_url") or result.get("url")
            print(f"[Cloudinary] Upload OK: {url} ({result.get('bytes',0)} bytes)")
            return url
            
        except ImportError:
            print("[Cloudinary] lib cloudinary non installée -> pip install cloudinary")
            raise
        except Exception as e:
            print(f"[Cloudinary] Echec upload: {e}")
            raise

    def delete_photo_cloudinary(self, photo_url: str) -> bool:
        """Supprime une photo de Cloudinary."""
        try:
            if "cloudinary.com" not in photo_url and "res.cloudinary.com" not in photo_url:
                return False
            
            import cloudinary
            import cloudinary.uploader
            from urllib.parse import urlparse
            
            cloudinary.config(
                cloud_name=CLOUDINARY_CLOUD_NAME,
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                secure=True
            )
            
            # Extrait public_id depuis URL
            # URL: https://res.cloudinary.com/cloud_name/image/upload/v123/immobile/xxxx.jpg
            # public_id = immobile/xxxx
            parsed = urlparse(photo_url)
            path = parsed.path
            
            # Trouve après /upload/
            if "/upload/" in path:
                after_upload = path.split("/upload/")[-1]
                # Enlève version v123456/
                parts = after_upload.split("/")
                if parts[0].startswith("v") and parts[0][1:].isdigit():
                    parts = parts[1:]
                public_id = "/".join(parts)
                # Enlève extension
                public_id = public_id.rsplit(".", 1)[0]
                
                result = cloudinary.uploader.destroy(public_id)
                print(f"[Cloudinary] Supprimé {public_id}: {result}")
                return result.get("result") == "ok"
            
            return False
            
        except Exception as e:
            print(f"[Cloudinary] Echec suppression {photo_url}: {e}")
            return False

    def upload_photo(self, file_path: str) -> str:
        src = Path(file_path)
        if not src.is_file():
            raise FileNotFoundError(f"fichier introuvable : {file_path}")
        data, suffix = self._prepare_image(file_path)
        if not data:
            raise ValueError("fichier vide")
        name = f"{new_id()}{suffix}"
        
        # 1. Essaie Cloudinary d'abord si configuré (Option B - 25 Go gratuit)
        if USE_CLOUDINARY:
            try:
                return self.upload_photo_cloudinary(data, name)
            except Exception as exc:
                print(f"[Cloudinary] echec, fallback Supabase/local: {exc}")
        
        # 2. Essaie Supabase Storage
        if self.mode == "supabase":
            try:
                self.client.storage.from_(SUPABASE_BUCKET).upload(name, data)
                return self.client.storage.from_(SUPABASE_BUCKET).get_public_url(name)
            except Exception as exc:
                print(f"[Storage] echec upload Supabase ({exc}), copie locale.")
        
        # 3. Fallback local
        LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = LOCAL_UPLOAD_DIR / name
        dest.write_bytes(data)
        return f"uploads/{name}"

    def subscribe_biens(self, callback) -> None:
        if self.mode != "supabase":
            return
        try:
            channel = self.client.channel("biens-changes")
            channel.on_postgres_changes(event="*", schema="public", table="biens", callback=callback).subscribe()
        except Exception as exc:
            print(f"[Realtime] non disponible: {exc}")

    def stats(self) -> Dict[str, Any]:
        users = self.list_users()
        biens = self.list_biens(only_active=False)
        by_country: Dict[str, int] = {}
        for u in users:
            code = u.get("country_code") or "??"
            by_country[code] = by_country.get(code, 0) + 1
        return {"users": len(users), "admins": sum(1 for u in users if u.get("role") == ROLE_SUPER_ADMIN), "blocked": sum(1 for u in users if u.get("is_blocked")), "biens": len(biens), "biens_active": sum(1 for b in biens if b.get("is_active")), "pending": sum(1 for b in biens if b.get("status") == STATUS_EN_ATTENTE), "by_country": by_country}

    def admin_uses_default_password(self) -> bool:
        admin = self.get_user_by_phone(APP_CONFIG.get("ADMIN_PHONE", ""))
        return bool(admin and admin.get("password_hash") == hash_password(APP_CONFIG.get("ADMIN_PASSWORD", "")))

    def ensure_admin_exists(self):
        try:
            phone = APP_CONFIG.get("ADMIN_PHONE")
            password = APP_CONFIG.get("ADMIN_PASSWORD", "admin123")
            if not phone:
                return
            admin = self.get_user_by_phone(phone)
            if not admin:
                print(f"[DB] Admin {phone} introuvable -> creation...")
                self.create_user(username="Super Admin", phone=phone, password=password, city="Douala", locality="Admin", email="kemezerael@gmail.com", country_code="CM")
                print(f"[DB] Admin {phone} cree")
                return
            patch: Dict[str, Any] = {}
            if admin.get("role") != ROLE_SUPER_ADMIN:
                patch["role"] = ROLE_SUPER_ADMIN
            if admin.get("is_blocked"):
                patch["is_blocked"] = False
            if APP_CONFIG.get("FORCE_ADMIN_ON_START", False):
                patch["password_hash"] = hash_password(password)
            if patch:
                self.update_user(admin["id"], patch)
                print(f"[DB] Admin {phone} remis en etat : {', '.join(patch)}")
        except Exception as e:
            print(f"[DB] Erreur ensure_admin_exists: {e}")


    # ---------- MAINTENANCE & GESTION STOCKAGE ----------
    def get_database_stats(self) -> Dict[str, Any]:
        """Statistiques complètes pour savoir ce qui prend de la place."""
        stats = {"mode": self.mode}
        
        if self.mode == "supabase":
            try:
                # Compte les biens
                biens = self.client.table("biens").select("id,photos,created_at,is_active", count="exact").execute()
                stats["biens_total"] = biens.count or len(biens.data or [])
                
                users = self.client.table("users").select("id", count="exact").execute()
                stats["users_total"] = users.count or 0
                
                favoris = self.client.table("favoris").select("id", count="exact").execute()
                stats["favoris_total"] = favoris.count or 0
                
                notifs = self.client.table("notifications").select("id", count="exact").execute()
                stats["notifications_total"] = notifs.count or 0
                
                alerts = self.client.table("user_alerts").select("id", count="exact").execute()
                stats["alerts_total"] = alerts.count or 0
                
                otps = self.client.table("otp_codes").select("id", count="exact").execute()
                stats["otp_codes_total"] = otps.count or 0
                
                # Storage - essaie de lister le bucket
                try:
                    files = self.client.storage.from_(SUPABASE_BUCKET).list()
                    total_size = sum(f.get("metadata", {}).get("size", 0) for f in files if isinstance(f, dict))
                    stats["storage_files"] = len(files)
                    stats["storage_size_mb"] = round(total_size / (1024*1024), 2)
                    stats["storage_size_bytes"] = total_size
                except Exception as e:
                    stats["storage_error"] = str(e)
                    stats["storage_files"] = "inconnu"
                
                # Biens inactifs / anciens
                old_biens = [b for b in (biens.data or []) if not b.get("is_active")]
                stats["biens_inactifs"] = len(old_biens)
                
            except Exception as e:
                stats["error"] = str(e)
        else:
            # Mode local
            stats["biens_total"] = len(self.data.get("biens", []))
            stats["users_total"] = len(self.data.get("users", []))
            stats["favoris_total"] = len(self.data.get("favoris", []))
            stats["notifications_total"] = len(self.data.get("notifications", []))
            stats["alerts_total"] = len(self.data.get("user_alerts", []))
            stats["otp_codes_total"] = len(self.data.get("otp_codes", []))
            
            # Taille dossiers locaux
            def dir_size(p: Path):
                if not p.exists():
                    return 0
                return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            
            stats["storage_size_bytes"] = dir_size(LOCAL_UPLOAD_DIR) + dir_size(WEB_UPLOAD_DIR)
            stats["storage_size_mb"] = round(stats["storage_size_bytes"] / (1024*1024), 2)
            stats["storage_files"] = len(list(LOCAL_UPLOAD_DIR.glob("*"))) if LOCAL_UPLOAD_DIR.exists() else 0
        
        # Limites Supabase gratuit
        stats["limits"] = {
            "database_free": "500 MB",
            "storage_free": "1 GB",
            "bandwidth_free": "5 GB/mois",
        }
        stats["storage_used_percent"] = round((stats.get("storage_size_bytes", 0) / (1024*1024*1024)) * 100, 2) if stats.get("storage_size_bytes") else 0
        
        return stats

    def delete_bien(self, bien_id: str) -> None:
        # 1. Récupère l'annonce pour avoir ses photos avant suppression
        bien = None
        try:
            bien = self.get_bien(bien_id)
        except:
            pass
        
        photos = (bien.get("photos") if bien else []) or []
        
        # 2. Supprime les fichiers physiques
        for photo_url in photos:
            if not photo_url:
                continue
            try:
                # Cloudinary
                if "cloudinary.com" in photo_url or "res.cloudinary.com" in photo_url:
                    if USE_CLOUDINARY:
                        self.delete_photo_cloudinary(photo_url)
                    # Supprime aussi copie locale si existe
                    try:
                        from urllib.parse import urlparse
                        fname = Path(urlparse(photo_url).path).name
                        local_copy = LOCAL_UPLOAD_DIR / fname
                        if local_copy.exists():
                            local_copy.unlink()
                    except:
                        pass
                    continue
                
                if photo_url.startswith("http"):
                    from urllib.parse import urlparse, unquote
                    parsed = urlparse(photo_url)
                    path = unquote(parsed.path)
                    if SUPABASE_BUCKET in path:
                        filename = path.split(SUPABASE_BUCKET + "/")[-1].lstrip("/")
                    else:
                        filename = Path(path).name
                    
                    if filename and self.mode == "supabase" and self.client:
                        try:
                            self.client.storage.from_(SUPABASE_BUCKET).remove([filename])
                            print(f"[Storage] Supprimé {filename} du bucket {SUPABASE_BUCKET}")
                        except Exception as e:
                            print(f"[Storage] Echec suppression {filename}: {e}")
                    
                    local_copy = LOCAL_UPLOAD_DIR / filename
                    if local_copy.exists():
                        local_copy.unlink()
                        print(f"[Storage] Supprimé local {local_copy}")
                
                else:
                    clean = photo_url.strip().lstrip("/")
                    candidates = [
                        Path(__file__).resolve().parent.parent / clean,
                        LOCAL_UPLOAD_DIR / Path(clean).name,
                        LOCAL_UPLOAD_DIR / clean,
                        WEB_UPLOAD_DIR / Path(clean).name,
                    ]
                    for p in candidates:
                        if p.is_file() and p.exists():
                            p.unlink()
                            print(f"[Storage] Supprimé local {p}")
                            break
            except Exception as e:
                print(f"[Storage] Erreur suppression photo {photo_url}: {e}")
        
        # 3. Supprime en base
        if self.mode == "supabase":
            try:
                self.client.table("favoris").delete().eq("bien_id", bien_id).execute()
            except:
                pass
            try:
                self.client.table("notifications").delete().eq("bien_id", bien_id).execute()
            except:
                pass
            try:
                self._safe_execute(self.client.table("biens").delete().eq("id", bien_id))
            except:
                self.client.table("biens").delete().eq("id", bien_id).execute()
            print(f"[DB] Annonce {bien_id} + {len(photos)} photos supprimées")
            return
        
        self.data["biens"] = [b for b in self.data["biens"] if b["id"] != bien_id]
        self.data["favoris"] = [f for f in self.data["favoris"] if f["bien_id"] != bien_id]
        self.data["notifications"] = [n for n in self.data["notifications"] if n.get("bien_id") != bien_id]
        self._save_local()
        print(f"[DB LOCAL] Annonce {bien_id} + {len(photos)} photos supprimées")

    def cleanup_orphan_photos(self) -> int:
        """Nettoie les photos dans assets/uploads qui ne sont plus référencées."""
        all_photos = set()
        for b in self.list_biens(only_active=False):
            for p in (b.get("photos") or []):
                if p:
                    if p.startswith("http"):
                        from urllib.parse import urlparse
                        all_photos.add(Path(urlparse(p).path).name)
                    else:
                        all_photos.add(Path(p).name)
        
        # Ajoute aussi les photos de profil
        for u in self.list_users():
            pp = u.get("profile_photo_url")
            if pp:
                if pp.startswith("http"):
                    from urllib.parse import urlparse
                    all_photos.add(Path(urlparse(pp).path).name)
                else:
                    all_photos.add(Path(pp).name)
        
        count = 0
        if LOCAL_UPLOAD_DIR.exists():
            for f in LOCAL_UPLOAD_DIR.iterdir():
                if f.is_file() and f.name not in all_photos:
                    if f.name.startswith("profile_") or f.name.startswith("avatar") or f.name.startswith("."):
                        continue
                    print(f"[Cleanup] Orphelin: {f}")
                    f.unlink()
                    count += 1
        
        if WEB_UPLOAD_DIR.exists() and WEB_UPLOAD_DIR != LOCAL_UPLOAD_DIR:
            for f in WEB_UPLOAD_DIR.iterdir():
                if f.is_file() and f.name not in all_photos:
                    if f.name.startswith("profile_") or f.name.startswith("."):
                        continue
                    print(f"[Cleanup] Orphelin web: {f}")
                    f.unlink()
                    count += 1
        
        print(f"[Cleanup] {count} photos orphelines supprimées")
        return count

    def cleanup_old_data(self, days_notifications=30, days_otps=2, days_inactive_biens=90) -> Dict[str, int]:
        """Nettoie les vieilles données qui prennent de la place."""
        result = {"notifications": 0, "otps": 0, "biens_inactifs": 0}
        
        from datetime import datetime, timedelta, timezone
        
        if self.mode == "supabase":
            # 1. Notifications > X jours
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days_notifications)).isoformat()
                # Supabase: delete where created_at < cutoff
                res = self.client.table("notifications").delete().lt("created_at", cutoff).execute()
                result["notifications"] = len(res.data or [])
                print(f"[Cleanup] {result['notifications']} vieilles notifications supprimées")
            except Exception as e:
                print(f"[Cleanup] Erreur notifications: {e}")
            
            # 2. OTP codes > X jours
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days_otps)).isoformat()
                res = self.client.table("otp_codes").delete().lt("created_at", cutoff).execute()
                result["otps"] = len(res.data or [])
                print(f"[Cleanup] {result['otps']} vieux OTP supprimés")
            except Exception as e:
                print(f"[Cleanup] Erreur OTP: {e}")
            
            # 3. Biens inactifs > X jours (optionnel - à activer manuellement)
            # On ne supprime pas automatiquement, on retourne juste le compte
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=days_inactive_biens)).isoformat()
                res = self.client.table("biens").select("id").eq("is_active", False).lt("created_at", cutoff).execute()
                result["biens_inactifs"] = len(res.data or [])
            except:
                pass
        
        else:
            # Mode local
            cutoff_notif = datetime.now(timezone.utc) - timedelta(days=days_notifications)
            cutoff_otp = datetime.now(timezone.utc) - timedelta(days=days_otps)
            
            before = len(self.data.get("notifications", []))
            self.data["notifications"] = [n for n in self.data.get("notifications", []) if datetime.fromisoformat(n.get("created_at","").replace("Z","+00:00")) > cutoff_notif]
            result["notifications"] = before - len(self.data["notifications"])
            
            before = len(self.data.get("otp_codes", []))
            self.data["otp_codes"] = [o for o in self.data.get("otp_codes", []) if datetime.fromisoformat(o.get("created_at","").replace("Z","+00:00")) > cutoff_otp]
            result["otps"] = before - len(self.data["otp_codes"])
            
            self._save_local()
        
        return result

    def delete_old_inactive_biens(self, days=90, dry_run=True) -> Dict[str, Any]:
        """Supprime les annonces inactives (non approuvées ou désactivées) vieilles de plus de X jours."""
        from datetime import datetime, timedelta, timezone
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        to_delete = []
        
        all_biens = self.list_biens(only_active=False)
        for b in all_biens:
            if not b.get("is_active"):
                try:
                    created = datetime.fromisoformat(b.get("created_at","").replace("Z","+00:00"))
                    if created < cutoff:
                        to_delete.append(b)
                except:
                    pass
        
        if dry_run:
            return {"count": len(to_delete), "biens": [{"id": b["id"], "titre": b.get("titre"), "created_at": b.get("created_at")} for b in to_delete], "dry_run": True}
        
        count = 0
        for b in to_delete:
            self.delete_bien(b["id"])
            count += 1
        
        return {"count": count, "dry_run": False}

    def optimize_storage(self) -> Dict[str, Any]:
        """Optimise tout: photos orphelines + vieilles données + rapport."""
        print("=== OPTIMISATION STOCKAGE ===")
        stats_before = self.get_database_stats()
        
        orphan = self.cleanup_orphan_photos()
        old = self.cleanup_old_data()
        
        stats_after = self.get_database_stats()
        
        return {
            "before": stats_before,
            "after": stats_after,
            "orphan_deleted": orphan,
            "old_data": old,
            "saved_mb": round((stats_before.get("storage_size_bytes",0) - stats_after.get("storage_size_bytes",0)) / (1024*1024), 2)
        }


db = Database()
db.ensure_admin_exists()
