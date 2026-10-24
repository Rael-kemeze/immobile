"""Remote Config - Active paiement et mises à jour depuis interface admin SANS republier APK."""

from __future__ import annotations
import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Cache local pour éviter trop d'appels
_CACHE: Dict[str, Any] = {}
_CACHE_TIME: float = 0
CACHE_TTL = 60  # 1 minute

DEFAULT_CONFIG = {
    "id": "main",
    "latest_version": "1.0.0",
    "version_code": 100,
    "min_required_version": "1.0.0",
    "min_required_code": 100,
    "enable_monetization": False,  # <- Tu actives paiement depuis admin UI
    "enable_boost_only": False,
    "enable_payments": False,
    "maintenance_mode": False,
    "maintenance_message": "Maintenance en cours, on revient vite !",
    "payment_methods": {
        "mtn_number": "6 70 12 34 56",
        "orange_number": "6 90 12 34 56",
        "whatsapp": "6 70 12 34 56"
    },
    "plans": {
        "FREE": {"max_listings": 3, "max_photos": 3},
        "BOOST": {"price": 1000, "duration_days": 7},
        "PRO": {"price": 5000, "duration_days": 30},
        "PREMIUM": {"price": 15000, "duration_days": 30}
    },
    "changelog": "",
    "download_url": "https://immobile.cm/download",
    "apk_url": "https://immobile.cm/download/immobile.apk",
    "force_update_message": "Mise à jour obligatoire pour continuer",
    "update_message": "Nouvelle version disponible avec améliorations",
    "created_at": "",
    "updated_at": ""
}

def get_remote_config(force_refresh: bool = False) -> Dict[str, Any]:
    """Récupère config depuis Supabase app_config, avec cache."""
    global _CACHE, _CACHE_TIME
    
    # Cache valide ?
    if not force_refresh and _CACHE and (time.time() - _CACHE_TIME) < CACHE_TTL:
        return _CACHE
    
    config = DEFAULT_CONFIG.copy()
    
    # 1. Depuis Supabase
    try:
        from services.db import db
        if hasattr(db, 'mode') and db.mode == "supabase":
            res = db._safe_execute(db.client.table("app_config").select("*").eq("id", "main").limit(1))
            if res.data and len(res.data) > 0:
                row = res.data[0]
                # Merge avec defaults
                for k, v in row.items():
                    if v is not None:
                        config[k] = v
                print(f"[RemoteConfig] Chargé depuis Supabase: monetization={config.get('enable_monetization')} v{config.get('latest_version')}")
                _CACHE = config
                _CACHE_TIME = time.time()
                return config
    except Exception as e:
        print(f"[RemoteConfig] Supabase error: {e}")
    
    # 2. Depuis fichier local version.json (fallback)
    try:
        from pathlib import Path
        local_path = Path(__file__).parent.parent / "version.json"
        if local_path.exists():
            data = json.loads(local_path.read_text())
            for k, v in data.items():
                if v is not None:
                    config[k] = v
            print(f"[RemoteConfig] Chargé depuis version.json")
            _CACHE = config
            _CACHE_TIME = time.time()
            return config
    except Exception as e:
        print(f"[RemoteConfig] version.json error: {e}")
    
    # 3. Depuis .env (fallback final)
    try:
        config["latest_version"] = os.getenv("APP_VERSION", config["latest_version"])
        config["version_code"] = int(os.getenv("APP_VERSION_CODE", str(config["version_code"])))
        config["enable_monetization"] = os.getenv("ENABLE_MONETIZATION", "false").lower() == "true"
        config["enable_boost_only"] = os.getenv("ENABLE_BOOST_ONLY", "false").lower() == "true"
    except:
        pass
    
    _CACHE = config
    _CACHE_TIME = time.time()
    return config

def is_monetization_enabled() -> bool:
    """Vérifie si paiement activé depuis admin UI"""
    cfg = get_remote_config()
    return bool(cfg.get("enable_monetization") or cfg.get("enable_payments"))

def is_boost_only() -> bool:
    cfg = get_remote_config()
    return bool(cfg.get("enable_boost_only"))

def is_maintenance() -> bool:
    cfg = get_remote_config()
    return bool(cfg.get("maintenance_mode"))

def get_payment_numbers() -> Dict[str, str]:
    cfg = get_remote_config()
    pm = cfg.get("payment_methods", {})
    return {
        "mtn": pm.get("mtn_number", DEFAULT_CONFIG["payment_methods"]["mtn_number"]),
        "orange": pm.get("orange_number", DEFAULT_CONFIG["payment_methods"]["orange_number"]),
        "whatsapp": pm.get("whatsapp", DEFAULT_CONFIG["payment_methods"]["whatsapp"])
    }

def get_version_info() -> Dict[str, Any]:
    cfg = get_remote_config()
    return {
        "latest_version": cfg.get("latest_version", "1.0.0"),
        "version_code": cfg.get("version_code", 100),
        "min_required_version": cfg.get("min_required_version", "1.0.0"),
        "min_required_code": cfg.get("min_required_code", 100),
        "changelog": cfg.get("changelog", ""),
        "download_url": cfg.get("download_url", ""),
        "apk_url": cfg.get("apk_url", ""),
        "force_message": cfg.get("force_update_message", ""),
        "update_message": cfg.get("update_message", "")
    }

def clear_cache():
    global _CACHE, _CACHE_TIME
    _CACHE = {}
    _CACHE_TIME = 0
