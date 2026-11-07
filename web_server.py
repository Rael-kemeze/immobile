"""IMMOBILE - serveur WEB de l'application REELLE (comptes, Supabase, Cloudinary).

Lancement local :  python web_server.py          puis ouvrir http://localhost:8000
Hebergement :      voir deploy_web/LISEZMOI.txt

Les secrets (SUPABASE_URL, SUPABASE_KEY, CLOUDINARY_*) se donnent en VARIABLES
D'ENVIRONNEMENT sur le serveur : ils ne sont jamais envoyes au navigateur.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("FLET_MAX_UPLOAD_SIZE", str(10 * 1024 * 1024))   # 10 Mo max par fichier
os.environ.setdefault("FLET_SERVER_IP", "0.0.0.0")
# Cle qui signe les liens d'envoi de fichiers (OBLIGATOIRE pour les photos en web).
# Sans elle : "Specify secret_key parameter or set FLET_SECRET_KEY". Les liens ne vivent que
# 10 min, donc une cle aleatoire a chaque demarrage suffit (ou fixez FLET_SECRET_KEY dans .env).
if not os.getenv("FLET_SECRET_KEY"):
    import secrets
    os.environ["FLET_SECRET_KEY"] = secrets.token_hex(32)

import flet as ft  # noqa: E402
import main as app  # noqa: E402
from services.db import WEB_UPLOAD_DIR, db  # noqa: E402

if db.mode != "supabase":
    print("=" * 70)
    print(" ATTENTION : Supabase n'est pas configure (SUPABASE_URL / SUPABASE_KEY).")
    print(" L'appli tourne sur une base LOCALE : sur un hebergeur gratuit, ces donnees")
    print(" sont PERDUES a chaque redemarrage. Configurez Supabase pour la mise en ligne.")
    print("=" * 70)

Path(WEB_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _clean_uploads(max_age: int = 3600) -> None:
    """Efface les fichiers temporaires d'envoi oublies (securite disque)."""
    while True:
        time.sleep(600)
        try:
            limit = time.time() - max_age
            for f in Path(WEB_UPLOAD_DIR).iterdir():
                if f.is_file() and f.stat().st_mtime < limit:
                    f.unlink()
        except Exception as exc:
            print(f"[WEB] nettoyage uploads : {exc}")


threading.Thread(target=_clean_uploads, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"[WEB] IMMOBILE web sur le port {port} (mode {db.mode})")
    ft.app(target=app.main, view=None, host="0.0.0.0", port=port,
           assets_dir="assets", upload_dir=str(WEB_UPLOAD_DIR))
