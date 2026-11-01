"""Splash FIX WHITE SCREEN + ft.Icons"""
import flet as ft
import time
import threading
from services.config import APP_CONFIG, COLORS
from services.auth_service import get_session, restore_session

# COMPAT
try:
    ICONS = ft.Icons
except AttributeError:
    ICONS = ft.Icons

def splash_view(page: ft.Page) -> ft.View:
    logo = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        controls=[
            ft.Container(width=90, height=90, bgcolor=COLORS["primary"], border_radius=24, alignment=ft.alignment.center, content=ft.Icon(ICONS.HOME_WORK_ROUNDED, size=48, color="white")),
            ft.Text(APP_CONFIG["APP_NAME"], size=32, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
            ft.Text("Immobilier pour tous - Cameroun", size=14, color=COLORS["muted"]),
            ft.Container(height=20),
            ft.ProgressRing(width=32, height=32, color=COLORS["primary"]),
            ft.Text(f"v{APP_CONFIG.get('APP_VERSION','1.0.0')} - Bafoussam", size=11, color=COLORS["muted"]),
        ]
    )
    def go_next():
        time.sleep(1.5)
        try:
            try:
                has_session = get_session(page) and restore_session(page)
            except:
                has_session = False
            page.go("/home" if has_session else "/login")
        except Exception as e:
            print(f"[Splash] {e}")
            try:
                page.go("/login")
            except:
                pass
    def check_update_async():
        time.sleep(2)
        try:
            from services.remote_config import get_remote_config
            get_remote_config(force_refresh=True)
        except:
            pass
    try:
        threading.Thread(target=check_update_async, daemon=True).start()
        threading.Thread(target=go_next, daemon=True).start()
    except:
        pass
    content = ft.Container(expand=True, alignment=ft.alignment.center, content=logo)
    return ft.View(route="/splash", bgcolor=COLORS["bg"], controls=[content])
