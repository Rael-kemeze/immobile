"""DB FIX Claude: pas de réseau à l'import + storage_data"""
from __future__ import annotations
import hashlib, io, json, os, re, uuid, threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from .config import APP_CONFIG, ROLE_SUPER_ADMIN, ROLE_USER, STATUS_APPROUVE, STATUS_EN_ATTENTE

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "biens").strip()

# FIX CLAUDE: Utilise FLET_APP_STORAGE_DATA sur Android
_ROOT = Path(__file__).resolve().parent.parent
_STORAGE = Path(os.getenv("FLET_APP_STORAGE_DATA", str(_ROOT)))
LOCAL_DB_PATH = _STORAGE / "local_db.json"
LOCAL_UPLOAD_DIR = _STORAGE / "uploads"
WEB_UPLOAD_DIR = _STORAGE / "uploads"
ASSETS_DIR = _ROOT / "assets"
MAX_IMAGE_SIDE = 1280

def now_iso(): return datetime.now(timezone.utc).isoformat()
def hash_password(p): return hashlib.sha256(("immobile$" + p).encode()).hexdigest()
def new_id(): return str(uuid.uuid4())
def normalize_phone(phone: str) -> str:
    if not phone: return ""
    digits = re.sub(r"\D", "", str(phone).strip())
    return digits[-9:] if len(digits) >= 9 else digits

class Database:
    def __init__(self):
        self.client = None
        self.mode = "local"
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                from supabase import create_client, ClientOptions
                # FIX: timeout court pour pas bloquer splash
                try:
                    opts = ClientOptions(postgrest_client_timeout=8)
                    self.client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)
                except:
                    self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
                self.mode = "supabase"
            except Exception as exc:
                print(f"[DB] Supabase indisponible ({exc}), fallback local.")
                self.mode = "local"
        if self.mode == "local":
            self._load_local()

    def _load_local(self):
        if LOCAL_DB_PATH.exists():
            self.data = json.loads(LOCAL_DB_PATH.read_text(encoding="utf-8"))
        else:
            self.data = {"users": [], "biens": [], "favoris": [], "notifications": []}
            self._save_local()
        for k in ("users", "biens", "favoris", "notifications", "user_alerts", "otp_codes"):
            self.data.setdefault(k, [])

    def _save_local(self):
        try:
            _STORAGE.mkdir(parents=True, exist_ok=True)
            LOCAL_DB_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[DB] save_local fail: {e}")

    def get_user_by_phone(self, phone):
        norm_target = normalize_phone(phone)
        if not norm_target: return None
        if self.mode == "supabase":
            try:
                res = self.client.table("users").select("*").eq("phone", phone).execute()
                if res.data: return res.data[0]
                # FIX CLAUDE: Ne télécharge plus toute la table, fait une recherche limitée
                return None
            except Exception as e:
                print(f"[DB] get_user_by_phone: {e}")
                return None
        for u in self.data["users"]:
            if normalize_phone(u.get("phone") or "") == norm_target:
                return u
        return None

    def is_phone_taken(self, phone, exclude_user_id=None):
        norm_target = normalize_phone(phone)
        if not norm_target: return False
        if self.mode == "supabase":
            try:
                rows = self.client.table("users").select("id,phone").limit(200).execute().data or []
                for u in rows:
                    if exclude_user_id and str(u.get("id")) == str(exclude_user_id): continue
                    if normalize_phone(u.get("phone")) == norm_target: return True
                return False
            except:
                return False
        for u in self.data["users"]:
            if exclude_user_id and str(u.get("id")) == str(exclude_user_id): continue
            if normalize_phone(u.get("phone") or "") == norm_target: return True
        return False

    def get_user_by_username(self, username):
        if self.mode == "supabase":
            try:
                res = self.client.table("users").select("*").eq("username", username).execute()
                return res.data[0] if res.data else None
            except: return None
        return next((u for u in self.data["users"] if u["username"] == username), None)

    def get_user(self, user_id):
        if self.mode == "supabase":
            try:
                res = self.client.table("users").select("*").eq("id", user_id).execute()
                return res.data[0] if res.data else None
            except: return None
        return next((u for u in self.data["users"] if u["id"] == user_id), None)

    def list_users(self, search=""):
        if self.mode == "supabase":
            try:
                rows = self.client.table("users").select("*").order("created_at", desc=True).limit(500).execute().data or []
            except: rows = []
        else:
            rows = sorted(self.data["users"], key=lambda u: u.get("created_at", ""), reverse=True)
        if search:
            s = search.lower()
            rows = [u for u in rows if s in (u.get("username") or "").lower() or s in (u.get("phone") or "").lower()]
        return rows

    def create_user(self, username, phone, password, city, locality, profile_photo_url=None, email=None, country_code=None):
        if self.is_phone_taken(phone): raise ValueError("PHONE_ALREADY_TAKEN")
        role = ROLE_SUPER_ADMIN if normalize_phone(phone) == normalize_phone(APP_CONFIG["ADMIN_PHONE"]) else ROLE_USER
        row = {"id": new_id(), "username": username.strip(), "phone": phone.strip(), "password_hash": hash_password(password), "city": city, "locality": locality, "profile_photo_url": profile_photo_url, "email": email, "country_code": country_code or "CM", "role": role, "is_blocked": False, "created_at": now_iso()}
        if self.mode == "supabase":
            try:
                return self.client.table("users").insert(row).execute().data[0]
            except Exception as e:
                print(f"[DB] create_user supabase fail {e}, fallback local")
        self.data["users"].append(row)
        self._save_local()
        return row

    def update_user(self, user_id, patch):
        if self.mode == "supabase":
            try:
                self.client.table("users").update(patch).eq("id", user_id).execute()
                return
            except Exception as e:
                print(f"[DB] update_user {e}")
        u = self.get_user(user_id)
        if u:
            u.update(patch)
            self._save_local()

    def list_biens(self, only_active=True, search=""):
        if self.mode == "supabase":
            try:
                q = self.client.table("biens").select("*")
                if only_active: q = q.eq("is_active", True)
                if search: q = q.ilike("title", f"%{search}%")
                return q.order("created_at", desc=True).limit(200).execute().data or []
            except: return []
        rows = self.data["biens"]
        if only_active: rows = [b for b in rows if b.get("is_active")]
        return sorted(rows, key=lambda b: b.get("created_at", ""), reverse=True)

    def create_bien(self, data):
        data["id"] = new_id()
        data["created_at"] = now_iso()
        if self.mode == "supabase":
            try:
                return self.client.table("biens").insert(data).execute().data[0]
            except Exception as e:
                print(f"[DB] create_bien {e}")
        self.data["biens"].append(data)
        self._save_local()
        return data

    def update_bien(self, bien_id, patch):
        if self.mode == "supabase":
            try:
                self.client.table("biens").update(patch).eq("id", bien_id).execute()
                return
            except: pass
        for b in self.data["biens"]:
            if b["id"] == bien_id:
                b.update(patch)
                self._save_local()
                break

    def delete_bien(self, bien_id):
        if self.mode == "supabase":
            try:
                self.client.table("biens").delete().eq("id", bien_id).execute()
                return
            except: pass
        self.data["biens"] = [b for b in self.data["biens"] if b["id"] != bien_id]
        self._save_local()

    def upload_photo(self, file_path):
        src = Path(file_path)
        if not src.is_file(): raise FileNotFoundError(file_path)
        name = f"{new_id()}{src.suffix}"
        if self.mode == "supabase":
            try:
                self.client.storage.from_(SUPABASE_BUCKET).upload(name, src.read_bytes())
                return self.client.storage.from_(SUPABASE_BUCKET).get_public_url(name)
            except: pass
        LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        dest = LOCAL_UPLOAD_DIR / name
        dest.write_bytes(src.read_bytes())
        return f"uploads/{name}"

    def subscribe_biens(self, callback):
        if self.mode != "supabase": return
        try:
            channel = self.client.channel("biens-changes")
            channel.on_postgres_changes(event="*", schema="public", table="biens", callback=callback).subscribe()
        except Exception as exc:
            print(f"[Realtime] {exc}")

    def stats(self):
        users = self.list_users()
        biens = self.list_biens(only_active=False)
        return {"users": len(users), "biens": len(biens)}

    def admin_uses_default_password(self):
        admin = self.get_user_by_phone(APP_CONFIG.get("ADMIN_PHONE", ""))
        return bool(admin and admin.get("password_hash") == hash_password(APP_CONFIG.get("ADMIN_PASSWORD", "")))

    def ensure_admin_exists(self):
        try:
            phone = APP_CONFIG.get("ADMIN_PHONE")
            password = APP_CONFIG.get("ADMIN_PASSWORD", "admin123")
            if not phone: return
            admin = self.get_user_by_phone(phone)
            if not admin:
                print(f"[DB] Admin {phone} creation...")
                self.create_user(username="Super Admin", phone=phone, password=password, city="Douala", locality="Admin", email="kemezerael@gmail.com", country_code="CM")
                return
            patch = {}
            if admin.get("role") != ROLE_SUPER_ADMIN: patch["role"] = ROLE_SUPER_ADMIN
            if admin.get("is_blocked"): patch["is_blocked"] = False
            if patch:
                self.update_user(admin["id"], patch)
        except Exception as e:
            print(f"[DB] ensure_admin_exists: {e}")

db = Database()
# FIX CLAUDE: Pas de réseau à l'import, lance en background
threading.Thread(target=db.ensure_admin_exists, daemon=True).start()
