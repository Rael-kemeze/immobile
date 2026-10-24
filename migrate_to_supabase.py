
"""Migration local_db.json -> Supabase"""
import json, os, uuid, re
from pathlib import Path
from dotenv import load_dotenv

for p in [Path(".env"), Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env", Path("/mnt/data/../.env")]:
    if p.exists():
        load_dotenv(dotenv_path=p, override=True)

from supabase import create_client

URL = os.getenv("SUPABASE_URL","").strip()
KEY = os.getenv("SUPABASE_KEY","").strip()
if not URL or not KEY:
    print("SUPABASE_URL/KEY manquant dans .env")
    exit(1)

supabase = create_client(URL, KEY)

LOCAL = Path(__file__).parent / "local_db.json"
if not LOCAL.exists():
    LOCAL = Path("/mnt/data/local_db.json")

data = json.loads(LOCAL.read_text())
print(f"Local: {len(data.get('users',[]))} users, {len(data.get('biens',[]))} biens")

id_map = {}

def is_uuid(s):
    try:
        uuid.UUID(str(s))
        return True
    except:
        return False

def normalize_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return digits[-9:] if len(digits)>=9 else digits

# 1. Users
for u in data.get("users",[]):
    old_id = u["id"]
    if not is_uuid(old_id):
        new_id = str(uuid.uuid4())
        id_map[old_id] = new_id
        u["id"] = new_id
        print(f"User {old_id} -> {new_id} ({u.get('username')})")
    else:
        id_map[old_id] = old_id

    payload = {
        "id": u["id"],
        "username": u.get("username"),
        "phone": u.get("phone"),
        "email": u.get("email"),
        "password_hash": u.get("password_hash"),
        "country_code": u.get("country_code") or u.get("country") or "CM",
        "city": u.get("city"),
        "locality": u.get("locality"),
        "role": u.get("role","USER"),
        "is_blocked": u.get("is_blocked", False),
        "created_at": u.get("created_at"),
    }
    payload = {k:v for k,v in payload.items() if v is not None}

    norm = normalize_phone(u.get("phone",""))
    existing = supabase.table("users").select("id,phone").execute().data or []
    exists = any(normalize_phone(e.get("phone"))==norm for e in existing)
    if exists:
        print(f"  SKIP user {u.get('phone')} déjà en Supabase")
        for e in existing:
            if normalize_phone(e.get("phone"))==norm:
                id_map[old_id]=e["id"]
        continue
    try:
        supabase.table("users").insert(payload).execute()
        print(f"  OK user {u.get('username')} {u.get('phone')}")
    except Exception as e:
        print(f"  ERR user {u.get('phone')}: {e}")

# 2. Biens
for b in data.get("biens",[]):
    old_uid = b.get("user_id")
    if old_uid in id_map:
        b["user_id"] = id_map[old_uid]
    if not is_uuid(b.get("id","")):
        b["id"] = str(uuid.uuid4())
    b.pop("user_phone", None)
    b.setdefault("status","APPROUVE")
    b.setdefault("is_active", True)
    allowed = ["id","user_id","titre","type_bien","transaction","categorie","country_code","city","locality","prix","prix_discutable","prix_sur_place","whatsapp","description","photos","chambres","salles_de_bain","salons","cuisine_interne","cuisine_externe","cuisine_type","superficie","status","is_active","is_featured","featured_until","created_at"]
    payload = {k:v for k,v in b.items() if k in allowed}
    try:
        supabase.table("biens").insert(payload).execute()
        print(f"  OK bien {b.get('titre')}")
    except Exception as e:
        print(f"  ERR bien {b.get('titre')}: {e}")

print("Migration terminée")
print("Mapping:", id_map)
