"""MAIN FINAL - Toutes routes + anti écran blanc"""
from __future__ import annotations
import os, traceback
from urllib.parse import parse_qs
import flet as ft

try:
    FT_ICONS = ft.Icons
except AttributeError:
    FT_ICONS = ft.icons

from services.auth import Session
from services.auth_service import get_session, restore_session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.db import WEB_UPLOAD_DIR, db
from services.i18n import init_lang, set_lang

# Imports avec fallback OTP
try:
    from views.auth_view import login_view, register_view, register_cgu_view, verify_otp_view
except ImportError:
    from views.auth_view import login_view, register_view
    def register_cgu_view(page):
        return ft.View(route="/cgu", controls=[ft.Text("CGU")])
    def verify_otp_view(page):
        page.go("/register")
        return ft.View(route="/verify-otp", controls=[])

from views.admin_view import admin_view
from views.alerts import alerts_view
from views.detail_view import detail_view
from views.home_view import home_view
from views.publish_view import publish_view
from views.settings import settings_view
from views.splash import splash_view
from views.user_views import favoris_view, mes_annonces_view, notifications_view, profile_view

def maintenance_view(page):
    return ft.View(route="/maintenance", bgcolor=COLORS["primary_dark"], padding=30, controls=[ft.Text("Maintenance", color="#FFFFFF")])

def error_view(page, route, error):
    return ft.View(route="/error", bgcolor="#FFFFFF", padding=20, controls=[
        ft.AppBar(title=ft.Text("Erreur"), bgcolor=COLORS["primary"]),
        ft.Column([
            ft.Icon(FT_ICONS.ERROR, size=64, color=COLORS["danger"]),
            ft.Text(f"Erreur sur {route}", weight=ft.FontWeight.BOLD, color=COLORS["danger"]),
            ft.Text(str(error), selectable=True),
            ft.ElevatedButton("Accueil", on_click=lambda e: page.go("/home")),
        ], scroll=ft.ScrollMode.AUTO)
    ])

def main(page: ft.Page):
    page.title = APP_CONFIG["APP_NAME"]
    page.bgcolor = COLORS["bg"]
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=COLORS["primary"])
    page.padding = 0
    init_lang(page)

    def route_change(e):
        raw = page.route or "/"
        route, _, query = raw.partition("?")
        print(f"[ROUTE] {raw}")
        try:
            if route.startswith("/lang/"):
                set_lang(page, route.split("/lang/", 1)[1].strip("/"))
                page.go("/home" if Session.user else "/login")
                return
            wanted = (parse_qs(query).get("lang") or [None])[0]
            if wanted in LANGUAGES:
                set_lang(page, wanted)

            page.views.clear()

            if APP_CONFIG.get("MAINTENANCE_MODE") and not Session.is_admin():
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
            elif route in ("/", "/login"):
                page.views.append(login_view(page))
            elif not Session.user:
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
        except Exception as ex:
            traceback.print_exc()
            page.views.clear()
            page.views.append(error_view(page, route, ex))
            page.update()

    def view_pop(e):
        if len(page.views) > 1:
            page.views.pop()
            page.go(page.views[-1].route)
        else:
            page.go("/home")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    try:
        db.subscribe_biens(lambda p=None: None)
    except:
        pass

    if get_session(page) and restore_session(page):
        page.go("/home")
    else:
        page.go("/splash")

if __name__ == "__main__":
    os.makedirs(WEB_UPLOAD_DIR, exist_ok=True)
    ft.app(target=main, assets_dir="assets", upload_dir=str(WEB_UPLOAD_DIR))
