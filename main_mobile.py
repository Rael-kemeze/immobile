"""IMMOBILE - Mode web pour tester sur mobile.


"""

from __future__ import annotations
import os
import socket
from urllib.parse import parse_qs
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons


from services.auth import Session
from services.auth_service import get_session, restore_session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.db import WEB_UPLOAD_DIR, db
from services.i18n import init_lang, set_lang, t
from views.admin_view import admin_view
from views.admin_remote_config_view import remote_config_view
from views.admin_storage_view import maintenance_view as storage_maintenance_view
from views.alerts import alerts_view
from views.auth_view import login_view, register_cgu_view, register_view, verify_otp_view
from views.forgot_password_view import forgot_password_view, verify_reset_otp_view, reset_password_view
from views.detail_view import detail_view
from views.home_view import home_view
from views.publish_view import publish_view
from views.settings import settings_view
from views.splash import splash_view
from views.user_views import (
    favoris_view,
    mes_annonces_view,
    notifications_view,
    profile_view,
)

def get_local_ip():
    """Récupère IP locale pour afficher QR code"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

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
            ft.Text("IMMOBILE sera de retour tres bientot. Merci de votre patience.", color="#DDE4DF", text_align=ft.TextAlign.CENTER),
        ],
    )

def main(page: ft.Page):
    # FIX deprecated warnings
    page.title = APP_CONFIG["APP_NAME"]
    page.bgcolor = COLORS["bg"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=COLORS["primary"])
    page.padding = 0
    # Nouveau API (pas deprecated)
    try:
        page.window.width = 400
        page.window.height = 860
    except:
        # Fallback ancien API si version Flet <0.23
        page.window_width = 400
        page.window_height = 860

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

        if route == "/splash":
            page.views.append(splash_view(page))
        elif route == "/register":
            page.views.append(register_view(page))
        elif route == "/cgu":
            page.views.append(register_cgu_view(page))
        elif route == "/verify-otp":
            page.views.append(verify_otp_view(page))
        elif route == "/forgot-password":
            page.views.append(forgot_password_view(page))
        elif route == "/verify-reset-otp":
            page.views.append(verify_reset_otp_view(page))
        elif route == "/reset-password":
            page.views.append(reset_password_view(page))
        elif route in ("/", "/login") or not Session.user:
            page.views.append(login_view(page))
        elif route == "/admin" and Session.is_admin():
            page.views.append(admin_view(page))
        elif route == "/admin/storage" and Session.is_admin():
            page.views.append(storage_maintenance_view(page))
        elif route.startswith("/bien/"):
            page.views.append(detail_view(page, route.split("/bien/")[1]))
        elif route == "/publish":
            page.views.append(publish_view(page))
        elif route.startswith("/edit/"):
            bid = route.split("/edit/")[1]
            page.views.append(publish_view(page, bien_id=bid))
        elif route == "/favoris":
            page.views.append(favoris_view(page))
        elif route == "/mes-annonces":
            page.views.append(mes_annonces_view(page))
        elif route == "/profile":
            page.views.append(profile_view(page))
        elif route == "/settings":
            page.views.append(settings_view(page))
        elif route == "/alerts":
            page.views.append(alerts_view(page))
        elif route == "/notifications":
            page.views.append(notifications_view(page))
        else:
            page.views.append(home_view(page))

        page.update()

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Désactive realtime (évite warning)
    # db.subscribe_biens() est désactivé en mode web

    if get_session(page) and restore_session(page):
        page.go("/home")
    else:
        page.go("/splash")


if __name__ == "__main__":
    os.makedirs(WEB_UPLOAD_DIR, exist_ok=True)
    
    ip = get_local_ip()
    print("\n" + "="*60)
    print("📱 IMMOBILE - MODE TEST TELEPHONE")
    print("="*60)
    print(f"✅ Serveur démarré !")
    print(f"")
    print(f"🌐 Sur ton ORDINATEUR: http://localhost:8550")
    print(f"📱 Sur ton TELEPHONE (même WiFi): http://{ip}:8550")
    print(f"")
    print(f"Instructions:")
    print(f"1. Connecte ton téléphone au même WiFi que ce PC")
    print(f"2. Ouvre Chrome sur ton téléphone")
    print(f"3. Va sur http://{ip}:8550")
    print(f"4. Teste l'app ! Publie, supprime, vérifie Cloudinary")
    print(f"")
    print(f"Pour arrêter: Ctrl+C")
    print("="*60 + "\n")
    
    ft.app(
        target=main, 
        assets_dir="assets", 
        upload_dir=str(WEB_UPLOAD_DIR),
        view=ft.AppView.WEB_BROWSER,
        port=8550,
        host="0.0.0.0",  # Accessible depuis téléphone
    )
