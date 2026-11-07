"""IMMOBILE - Application immobiliere internationale.

Flet 0.28.3 / Python 3.11+
Lancement :  python main.py
"""

from __future__ import annotations

import importlib
import os
import time
import traceback
from urllib.parse import parse_qs

import flet as ft
try:
    FT_ICONS = ft.Icons
except Exception:
    FT_ICONS = ft.icons

from services.visitor import SessionFactory as _SessionClass
from services.config import APP_CONFIG, COLORS, LANGUAGES
from pathlib import Path as _Path

UPLOAD_DIR = _Path(os.getenv("FLET_APP_STORAGE_DATA") or _Path(__file__).parent) / "uploads"
WEB_UPLOAD_DIR = UPLOAD_DIR  # meme chemin que services.db, sans importer db au demarrage
from services.i18n import init_lang, set_lang


def _view(module: str, name: str):
    """Charge une vue a la demande.

    Un probleme dans UNE vue (import, icone inconnue...) ne bloque plus tout le
    demarrage : l'erreur s'affiche a l'ecran au lieu d'une page blanche.
    """
    return getattr(importlib.import_module(module), name)


def maintenance_view(page: ft.Page) -> ft.View:
    return ft.View(
        route="/maintenance",
        bgcolor=COLORS["primary_dark"],
        padding=30,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(FT_ICONS.BUILD_CIRCLE, size=80, color=COLORS["accent"]),
            ft.Text("Maintenance en cours", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text(
                "IMMOBILE sera de retour tres bientot. Merci de votre patience.",
                color="#DDE4DF",
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )


def error_view(page: ft.Page, details: str) -> ft.View:
    """Ecran d'erreur : remplace la page blanche silencieuse."""
    return ft.View(
        route="/error",
        bgcolor="#FFFFFF",
        padding=16,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Icon(FT_ICONS.ERROR_OUTLINE, size=48, color=COLORS["danger"]),
            ft.Text("Une erreur est survenue", size=20, weight=ft.FontWeight.BOLD, color=COLORS["danger"]),
            ft.Text("Faites une capture d'ecran de cette page pour la corriger.", size=12, color=COLORS["muted"]),
            ft.Text(details, size=10, selectable=True),
            ft.ElevatedButton(
                "Reessayer",
                # le "?r=" force un vrai changement de route meme si on y est deja
                on_click=lambda e: page.go(f"/splash?r={time.time_ns()}"),
            ),
        ],
    )


def show_error(page: ft.Page) -> None:
    details = traceback.format_exc()
    print("[IMMOBILE] ERREUR :\n" + details)
    try:
        page.views.clear()
        page.views.append(error_view(page, details[-1800:]))
        page.update()
    except Exception:
        pass


def setup_app(page: ft.Page) -> None:
    Session = _SessionClass.bind(page)
    page.title = APP_CONFIG["APP_NAME"]
    page.bgcolor = COLORS["bg"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=COLORS["primary"])
    page.padding = 0
    try:
        page.window.width = 400
        page.window.height = 860
    except Exception:
        try:
            page.window_width = 400
            page.window_height = 860
        except Exception:
            pass

    init_lang(page)

    def route_change(e: ft.RouteChangeEvent):
        raw_route = page.route or "/"
        route, _, query = raw_route.partition("?")

        if route.startswith("/lang/"):
            set_lang(page, route.split("/lang/", 1)[1].strip("/"))
            page.go("/home" if Session.user else "/login")
            return
        wanted = (parse_qs(query).get("lang") or [None])[0]
        if wanted in LANGUAGES:
            set_lang(page, wanted)

        page.views.clear()

        if APP_CONFIG["MAINTENANCE_MODE"] and not Session.is_admin():
            page.views.append(maintenance_view(page))
            page.update()
            return

        # Routes publiques
        if route == "/splash":
            view = _view("views.splash", "splash_view")(page)
        elif route == "/register":
            view = _view("views.auth_view", "register_view")(page)
        elif route == "/cgu":
            view = _view("views.auth_view", "register_cgu_view")(page)
        elif route == "/verify-otp":
            view = _view("views.auth_view", "verify_otp_view")(page)
        elif route == "/forgot-password":
            view = _view("views.forgot_password_view", "forgot_password_view")(page)
        elif route == "/verify-reset-otp":
            view = _view("views.forgot_password_view", "verify_reset_otp_view")(page)
        elif route == "/reset-password":
            view = _view("views.forgot_password_view", "reset_password_view")(page)
        elif route in ("/", "/login") or not Session.user:
            view = _view("views.auth_view", "login_view")(page)
        # Routes privees
        elif route == "/admin" and Session.is_admin():
            view = _view("views.admin_view", "admin_view")(page)
        elif route == "/admin/storage" and Session.is_admin():
            view = _view("views.admin_storage_view", "maintenance_view")(page)
        elif route == "/admin/remote" and Session.is_admin():
            view = _view("views.admin_remote_config_view", "remote_config_view")(page)
        elif route.startswith("/bien/"):
            view = _view("views.detail_view", "detail_view")(page, route.split("/bien/")[1])
        elif route == "/publish":
            view = _view("views.publish_view", "publish_view")(page)
        elif route.startswith("/edit/"):
            view = _view("views.publish_view", "publish_view")(page, bien_id=route.split("/edit/")[1])
        elif route == "/favoris":
            view = _view("views.user_views", "favoris_view")(page)
        elif route == "/mes-annonces":
            view = _view("views.user_views", "mes_annonces_view")(page)
        elif route == "/profile":
            view = _view("views.user_views", "profile_view")(page)
        elif route == "/settings":
            view = _view("views.settings", "settings_view")(page)
        elif route == "/alerts":
            view = _view("views.alerts", "alerts_view")(page)
        elif route == "/notifications":
            view = _view("views.user_views", "notifications_view")(page)
        else:
            view = _view("views.home_view", "home_view")(page)

        page.views.append(view)
        page.update()

    def safe_route_change(e: ft.RouteChangeEvent):
        # Si la construction d'une vue plante, on affiche l'erreur au lieu de
        # laisser la liste des vues vide (= page blanche).
        try:
            route_change(e)
        except Exception:
            show_error(page)

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.go(page.views[-1].route)

    page.on_route_change = safe_route_change
    page.on_view_pop = view_pop

    # Aucun appel reseau ici : on affiche TOUT DE SUITE le splash. C'est lui qui
    # restaure la session en arriere-plan (voir views/splash.py).
    # Le temps reel (db.subscribe_biens) n'est plus lance au demarrage : il n'est
    # pas indispensable et pouvait retarder l'affichage sur mobile.
    def _on_lifecycle(e):
        # Retour au premier plan : force le redessin (evite l'ecran blanc sous Android)
        state = str(getattr(e, "data", "") or getattr(e, "state", "")).lower()
        print(f"[LIFECYCLE] {state}")
        if "resume" not in state:
            return

        def _refresh():
            import time
            for delay in (0.0, 0.4, 1.2):
                time.sleep(delay)
                try:
                    if not page.views:
                        page.go("/splash")
                    else:
                        page.update()
                except Exception as exc:
                    print(f"[LIFECYCLE] erreur : {exc}")

        import threading
        threading.Thread(target=_refresh, daemon=True).start()

    page.on_app_lifecycle_state_change = _on_lifecycle
    page.go("/splash")


def main(page: ft.Page):
    try:
        setup_app(page)
    except Exception:
        show_error(page)


if __name__ == "__main__":
    try:
        os.makedirs(WEB_UPLOAD_DIR, exist_ok=True)
    except Exception as exc:
        print(f"[IMMOBILE] dossier uploads non cree ({exc})")
    ft.app(target=main, assets_dir="assets", upload_dir=str(WEB_UPLOAD_DIR))
