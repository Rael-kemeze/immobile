"""Réinitialise le compte administrateur (mode LOCAL ou SUPABASE).

À placer à la racine du projet (à côté de main.py), puis :

    python reset_admin.py                  # mot de passe = ADMIN_PASSWORD de config.py
    python reset_admin.py MonMotDePasse1   # ou un mot de passe de votre choix

Le script affiche aussi le mode de base de données réellement utilisé
(LOCAL ou SUPABASE), ce qui permet de savoir où l'app lit ses comptes.
"""

import sys

from services.config import APP_CONFIG, ROLE_SUPER_ADMIN
from services.db import db, hash_password

phone = APP_CONFIG["ADMIN_PHONE"]
password = sys.argv[1] if len(sys.argv) > 1 else APP_CONFIG["ADMIN_PASSWORD"]

print(f"Mode base de données : {db.mode.upper()}")

user = db.get_user_by_phone(phone)
if user:
    db.update_user(
        user["id"],
        {
            "password_hash": hash_password(password),
            "role": ROLE_SUPER_ADMIN,
            "is_blocked": False,
        },
    )
    print(f"Compte {phone} réinitialisé (rôle SUPER_ADMIN, débloqué).")
else:
    db.create_user("Super Admin", phone, password, "Douala", "Admin", country_code="CM")
    print(f"Compte {phone} créé.")

print(f"Connexion : numéro exact {phone} + le mot de passe choisi.")
