"""Splash avec vérification mise à jour - Pour site officiel."""

from __future__ import annotations
import flet as ft
from services.config import APP_CONFIG, COLORS
from services.auth_service import get_session, restore_session
from services.db import db
from components.widgets import snack

def splash_view(page: ft.Page) -> ft.View:
    # Vérifie mise à jour en arrière-plan
    def check_update():
        try:
            from services.update_service import update_service, APP_VERSION
            info = update_service.check_for_update()
            if info["has_update"]:
                print(f"[Update] Nouvelle version {info['latest_version']} disponible (actuelle {APP_VERSION})")
                # Affiche bannière si pas forcée, ou dialogue si forcée
                if info["is_forced"]:
                    show_forced_update(page, info)
                else:
                    show_update_banner(page, info)
        except Exception as e:
            print(f"[Update] Check error: {e}")
    
    def show_update_banner(page: ft.Page, info: dict):
        def reload_app(e):
            page.go("/splash")
            page.update()
            # Pour web: recharge la page
            try:
                page.launch_url("/")  # ou location.reload via JS
            except:
                pass
            page.go("/home")
        
        banner = ft.Container(
            bgcolor="#FFF3CD", border_radius=10, padding=12,
            border=ft.border.all(1, "#FFC107"),
            content=ft.Column(spacing=6, controls=[
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.icons.SYSTEM_UPDATE, color="#856404"),
                    ft.Text(f"Nouvelle version {info['latest_version']} disponible !", weight=ft.FontWeight.BOLD, color="#856404", size=13),
                ]),
                ft.Text(info.get("changelog","Améliorations et corrections"), size=11, color="#856404"),
                ft.Row(spacing=8, controls=[
                    ft.ElevatedButton("Mettre à jour", icon=ft.icons.REFRESH, on_click=reload_app, bgcolor="#FFC107", color="#000"),
                    ft.TextButton("Plus tard", on_click=lambda e: setattr(banner, 'visible', False) or page.update()),
                ])
            ])
        )
        # Ajoute en haut de la page si possible
        try:
            page.snack_bar = ft.SnackBar(content=ft.Text(f"Version {info['latest_version']} disponible - Rechargez la page"), action="Recharger", on_action=reload_app)
            page.snack_bar.open = True
            page.update()
        except:
            pass
    
    def show_forced_update(page: ft.Page, info: dict):
        def update_now(e):
            url = info.get("download_url") or "/"
            try:
                page.launch_url(url)
            except:
                page.go("/")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Mise à jour obligatoire"),
            content=ft.Column(spacing=10, tight=True, controls=[
                ft.Text(f"Version {info['latest_version']} requise (tu as {info['current_version']})"),
                ft.Text(info.get("message") or info.get("changelog") or "Cette mise à jour corrige des bugs importants.", size=12),
            ]),
            actions=[ft.ElevatedButton("Mettre à jour maintenant", on_click=update_now, bgcolor=COLORS["primary"], color="white")]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    # Lance vérif après 2 sec
    import threading
    threading.Timer(2.0, check_update).start()

    # Splash normal
    logo = ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
        controls=[
            ft.Container(width=90, height=90, bgcolor=COLORS["primary"], border_radius=24, alignment=ft.alignment.center,
                content=ft.Icon(ft.icons.HOME_WORK_ROUNDED, size=48, color="white")),
            ft.Text(APP_CONFIG["APP_NAME"], size=32, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
            ft.Text("Immobilier pour tous", size=14, color=COLORS["muted"]),
            ft.Container(height=20),
            ft.ProgressRing(width=32, height=32, color=COLORS["primary"]),
            ft.Text(f"v{APP_CONFIG.get('APP_VERSION','1.0.0')}", size=11, color=COLORS["muted"]),
        ]
    )

    def go_next(e=None):
        # Restore session
        try:
            if get_session(page) and restore_session(page):
                page.go("/home")
            else:
                page.go("/login")
        except:
            page.go("/login")

    # Auto-navigate après 1.5s
    threading.Timer(1.5, lambda: page.go("/home") if False else go_next()).start()

    content = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=logo
    )

    return ft.View(route="/splash", bgcolor=COLORS["bg"], controls=[content])
