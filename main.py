"""IMMOBILE - FIX Claude: splash immédiat + erreur visible"""
from __future__ import annotations
import os
import traceback
import threading
from urllib.parse import parse_qs
import flet as ft

from services.auth import Session
from services.auth_service import get_session, restore_session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.db import WEB_UPLOAD_DIR, db
from services.i18n import init_lang, set_lang

try:
    ICONS = ft.Icons
except:
    ICONS = ft.icons

def maintenance_view(page: ft.Page) -> ft.View:
    return ft.View(route="/maintenance", bgcolor=COLORS["primary_dark"], padding=30, vertical_alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Icon(ICONS.BUILD_CIRCLE, size=80, color=COLORS["accent"]), ft.Text("Maintenance", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF")])

def main(page: ft.Page):
    page.title = APP_CONFIG["APP_NAME"]
    page.bgcolor = COLORS["bg"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=COLORS["primary"])
    page.padding = 0
    try:
        page.window.width = 400
        page.window.height = 860
    except:
        try:
            page.window_width = 400
            page.window_height = 860
        except:
            pass
    init_lang(page)

    def show_error(title, err):
        tb = traceback.format_exc()
        print(f"[CRASH] {title}: {err}\n{tb}")
        page.views.clear()
        page.views.append(ft.View(route="/error", bgcolor="#FFFFFF", scroll=ft.ScrollMode.AUTO, controls=[ft.Container(padding=20, content=ft.Column(spacing=10, controls=[ft.Icon(ICONS.ERROR, size=60, color="red"), ft.Text("Erreur", size=24, weight=ft.FontWeight.BOLD, color="red"), ft.Text(f"{title}: {err}", color="black", selectable=True), ft.Container(bgcolor="#FFE0E0", padding=10, border_radius=8, content=ft.Text(tb[-3000:], size=10, color="black", selectable=True)), ft.ElevatedButton("Login", on_click=lambda e: page.go("/login"))]))]))
        try:
            page.update()
        except:
            pass

    def route_change(e: ft.RouteChangeEvent):
        try:
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
            from views.splash import splash_view
            from views.auth_view import login_view, register_view, register_cgu_view, verify_otp_view
            from views.home_view import home_view
            from views.publish_view import publish_view
            from views.detail_view import detail_view
            from views.admin_view import admin_view
            from views.settings import settings_view
            from views.alerts import alerts_view
            from views.user_views import favoris_view, mes_annonces_view, notifications_view, profile_view

            if route == "/splash":
                page.views.append(splash_view(page))
            elif route == "/register":
                page.views.append(register_view(page))
            elif route == "/cgu":
                page.views.append(register_cgu_view(page))
            elif route == "/verify-otp":
                page.views.append(verify_otp_view(page))
            elif route in ("/", "/login") or not Session.user:
                page.views.append(login_view(page))
            elif route == "/admin" and Session.is_admin():
                page.views.append(admin_view(page))
            elif route.startswith("/bien/"):
                page.views.append(detail_view(page, route.split("/bien/")[1]))
            elif route == "/publish":
                page.views.append(publish_view(page))
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
        except Exception as err:
            show_error(f"route {page.route}", err)

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    def on_biens_change(payload=None):
        try:
            if page.route == "/home":
                page.go("/home")
        except:
            pass
    db.subscribe_biens(on_biens_change)

    # FIX CLAUDE: Affiche splash IMMEDIATEMENT, pas de restore_session bloquant
    page.go("/splash")

if __name__ == "__main__":
    os.makedirs(WEB_UPLOAD_DIR, exist_ok=True)
    try:
        ft.app(target=main, assets_dir="assets", upload_dir=str(WEB_UPLOAD_DIR))
    except AttributeError:
        try:
            ft.run(main)
        except:
            import flet
            flet.app(target=main)
