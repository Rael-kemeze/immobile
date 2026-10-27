"""Espace administrateur : chiffres clés, mot de passe admin, utilisateurs + gestion stockage."""

from __future__ import annotations
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons

from components.widgets import avatar, badge, password_card, snack, stat_card, text_field
from services.auth import Session
from services.config import COLORS, ROLE_SUPER_ADMIN
from services.countries import country_name, get_country
from services.db import db
from services.i18n import t

MAX_USERS_SHOWN = 200

def admin_view(page: ft.Page) -> ft.View:
    if not Session.is_admin():
        page.go("/home")
        return ft.View(route="/admin")

    me = Session.user
    stats_box = ft.Column(spacing=10)
    countries_box = ft.Column(spacing=6)
    users_box = ft.Column(spacing=8)
    search = text_field(t("admin_search_users"), prefix_icon=FT_ICONS.SEARCH)

    def build_stats():
        s = db.stats()
        stats_box.controls = [
            ft.Row(spacing=10, controls=[
                stat_card(FT_ICONS.GROUP, t("admin_stat_users"), s["users"], COLORS["primary"]),
                stat_card(FT_ICONS.BLOCK, t("admin_stat_blocked"), s["blocked"], COLORS["danger"]),
            ]),
            ft.Row(spacing=10, controls=[
                stat_card(FT_ICONS.HOME_WORK_OUTLINED, t("admin_stat_listings"), s["biens_active"], COLORS["accent"]),
                stat_card(FT_ICONS.ADMIN_PANEL_SETTINGS_OUTLINED, t("admin_stat_admins"), s["admins"], COLORS["primary_dark"]),
            ]),
        ]
        rows = []
        for code, count in sorted(s["by_country"].items(), key=lambda kv: (-kv[1], kv[0])):
            c = get_country(code) if code != "??" else None
            name = f"{c['flag']} {country_name(c)}" if c else code
            rows.append(
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text(name, size=13),
                    ft.Text(str(count), weight=ft.FontWeight.BOLD, size=13),
                ])
            )
        countries_box.controls = rows

    def toggle_block(u):
        blocked = bool(u.get("is_blocked"))
        db.update_user(u["id"], {"is_blocked": not blocked})
        snack(page, t("user_unblocked") if blocked else t("user_blocked"))
        refresh()

    def user_row(u):
        is_blocked = bool(u.get("is_blocked"))
        is_admin_row = u.get("role") == ROLE_SUPER_ADMIN
        c = get_country(u.get("country_code"))
        badges = []
        if is_admin_row:
            badges.append(badge(t("role_admin"), COLORS["accent"], "#12211A"))
        if is_blocked:
            badges.append(badge(t("badge_blocked"), COLORS["danger"]))
        action = None
        if not is_admin_row and u["id"] != me["id"]:
            action = ft.OutlinedButton(
                t("unblock_button") if is_blocked else t("block_button"),
                on_click=lambda e, u=u: toggle_block(u),
                style=ft.ButtonStyle(
                    color=COLORS["primary"] if is_blocked else COLORS["danger"],
                    side=ft.BorderSide(1, COLORS["primary"] if is_blocked else COLORS["danger"]),
                ),
            )
        return ft.Container(
            bgcolor="#FFFFFF", border_radius=14, padding=10, border=ft.border.all(1, "#E0E4E1"),
            content=ft.Row(spacing=10, controls=[
                avatar(u, 42),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text(u.get("username",""), weight=ft.FontWeight.W_600, size=14),
                    ft.Text(f"{u.get('phone','')} - {c['flag']} {u.get('city') or ''}", size=12, color=COLORS["muted"]),
                    ft.Row(spacing=6, controls=badges) if badges else ft.Container(height=0),
                ]),
                action or ft.Container(width=0),
            ]),
        )

    def build_users():
        rows = db.list_users(search.value or "")
        if not rows:
            users_box.controls = [ft.Text(t("no_users_found"), color=COLORS["muted"])]
            return
        users_box.controls = [user_row(u) for u in rows[:MAX_USERS_SHOWN]]

    def refresh(e=None):
        build_stats()
        build_users()
        page.update()

    search.on_change = lambda e: (build_users(), page.update())
    build_stats()
    build_users()

    warning = []
    if db.admin_uses_default_password():
        warning = [
            ft.Container(bgcolor="#FFF4E5", border=ft.border.all(1, COLORS["accent"]), border_radius=12, padding=12,
                content=ft.Row(spacing=10, controls=[
                    ft.Icon(FT_ICONS.WARNING_AMBER_ROUNDED, color=COLORS["accent"]),
                    ft.Text(t("admin_default_password_warning"), size=13, expand=True),
                ]),
            ),
            ft.Container(height=10),
        ]

    def section(title):
        return ft.Container(padding=ft.padding.only(top=18, bottom=8),
            content=ft.Text(title, weight=ft.FontWeight.BOLD, size=15, color=COLORS["text"]))

    return ft.View(
        route="/admin",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text(t("admin_space"), color="#FFFFFF", weight=ft.FontWeight.BOLD),
            bgcolor=COLORS["primary"],
            leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/home")),
            actions=[ft.IconButton(FT_ICONS.REFRESH, icon_color="#FFFFFF", on_click=refresh)],
        ),
        controls=[
            *warning,
            stats_box,
            
            # === BOUTON GESTION STOCKAGE ===
            ft.Container(height=12),
            ft.Container(
                bgcolor="#E8F5E9", border_radius=14, padding=12, border=ft.border.all(1, COLORS["primary"]),
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[
                        ft.Icon(FT_ICONS.STORAGE, color=COLORS["primary"], size=28),
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text("Gestion Base de Données & Stockage", weight=ft.FontWeight.BOLD, size=15),
                            ft.Text("Vérifie espace utilisé, nettoie photos orphelines, vieilles notifications", size=11, color=COLORS["muted"]),
                        ])
                    ]),
                    ft.ElevatedButton(
                        "Ouvrir Gestion Stockage",
                        icon=FT_ICONS.CLEANING_SERVICES,
                        on_click=lambda e: page.go("/admin/storage"),
                        style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF"),
                        expand=True,
                    ),
                ])
            ),
            ft.Container(height=12),
            ft.Container(
                bgcolor="#FFF3CD", border_radius=14, padding=12, border=ft.border.all(1, "#FF9800"),
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=10, controls=[
                        ft.Icon(FT_ICONS.SYSTEM_UPDATE, color="#FF9800", size=28),
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text("Contrôle à Distance APK & Paiement", weight=ft.FontWeight.BOLD, size=15),
                            ft.Text("Active/désactive paiement, force mises à jour APK SANS republier", size=11, color=COLORS["muted"]),
                        ])
                    ]),
                    ft.ElevatedButton(
                        "Ouvrir Contrôle à Distance",
                        icon=FT_ICONS.SETTINGS_REMOTE,
                        on_click=lambda e: page.go("/admin/remote"),
                        style=ft.ButtonStyle(bgcolor="#FF9800", color="#FFFFFF"),
                        expand=True,
                    ),
                ])
            ),
            
            section(t("admin_password_title")),
            password_card(page, t("admin_password_title")),
            section(t("admin_users_by_country")),
            ft.Container(bgcolor="#FFFFFF", border_radius=16, padding=14, border=ft.border.all(1, "#E0E4E1"), content=countries_box),
            section(t("admin_users_list")),
            search,
            ft.Container(height=6),
            users_box,
            ft.Container(height=30),
        ],
    )
