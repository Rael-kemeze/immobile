"""Splash avec vérification mise à jour automatique."""

from __future__ import annotations
import flet as ft
import threading
import time
from services.config import APP_CONFIG, COLORS
from services.auth_service import get_session, restore_session
from services.i18n import t

def splash_view(page: ft.Page) -> ft.View:
    
    # Vérifie mise à jour en arrière-plan
    def check_update_async():
        time.sleep(1.5)
        try:
            from services.remote_config import get_remote_config
            cfg = get_remote_config(force_refresh=True)
            current_code = int(APP_CONFIG.get("APP_VERSION_CODE", 100))
            latest_code = cfg.get("version_code", 100)
            min_code = cfg.get("min_required_code", 100)
            
            print(f"[Update] Check: current={current_code} latest={latest_code} min={min_code} monetization={cfg.get('enable_monetization')}")
            
            # Si mise à jour forcée
            if min_code > current_code:
                show_forced_dialog(cfg)
            elif latest_code > current_code:
                show_update_snack(cfg)
                
        except Exception as e:
            print(f"[Update] Error: {e}")
    
    def show_update_snack(cfg):
        try:
            def reload_action(e):
                page.go("/splash")
                page.update()
                time.sleep(0.5)
                page.go("/home")
            
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"🚀 Nouvelle version {cfg.get('latest_version')} disponible ! {cfg.get('update_message','')}"),
                action="Recharger",
                on_action=reload_action,
                duration=8000
            )
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            print(f"[Update] Snack error: {ex}")
    
    def show_forced_dialog(cfg):
        try:
            def update_now(e):
                url = cfg.get("apk_url") or cfg.get("download_url") or "https://immobile.cm"
                page.launch_url(url)
                page.dialog.open = False
                page.update()
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Mise à jour obligatoire"),
                content=ft.Column(tight=True, spacing=10, controls=[
                    ft.Icon(ft.icons.SYSTEM_UPDATE, size=48, color=COLORS["primary"]),
                    ft.Text(f"Version {cfg.get('latest_version')} requise (tu as {APP_CONFIG.get('APP_VERSION','1.0.0')})", weight=ft.FontWeight.BOLD),
                    ft.Text(cfg.get("force_update_message") or cfg.get("changelog") or "Cette mise à jour est obligatoire pour continuer.", size=12),
                ]),
                actions=[ft.ElevatedButton("Mettre à jour", on_click=update_now, bgcolor=COLORS["primary"], color="white")]
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
        except Exception as ex:
            print(f"[Forced] Dialog error: {ex}")

    # Lancer check en background
    threading.Thread(target=check_update_async, daemon=True).start()

    # UI Splash
    logo = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        controls=[
            ft.Container(width=90, height=90, bgcolor=COLORS["primary"], border_radius=24, alignment=ft.alignment.center,
                content=ft.Icon(ft.icons.HOME_WORK_ROUNDED, size=48, color="white")),
            ft.Text(APP_CONFIG["APP_NAME"], size=32, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
            ft.Text("Immobilier pour tous - Cameroun", size=14, color=COLORS["muted"]),
            ft.Container(height=20),
            ft.ProgressRing(width=32, height=32, color=COLORS["primary"]),
            ft.Text(f"v{APP_CONFIG.get('APP_VERSION','1.0.0')} - Bafoussam", size=11, color=COLORS["muted"]),
        ]
    )

    def go_next():
        time.sleep(1.2)
        try:
            if get_session(page) and restore_session(page):
                page.go("/home")
            else:
                page.go("/login")
        except:
            page.go("/login")

    threading.Thread(target=go_next, daemon=True).start()

    content = ft.Container(expand=True, alignment=ft.alignment.center, content=logo)
    return ft.View(route="/splash", bgcolor=COLORS["bg"], controls=[content])
