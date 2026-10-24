"""Conditions generales d'utilisation - a valider avant finalisation du compte."""

from __future__ import annotations

import flet as ft

from components.widgets import primary_button, snack
from services.config import COLORS
from services.i18n import t


def cgu_view(page: ft.Page, on_accept) -> ft.View:
    """`on_accept` est appele quand l'utilisateur a coche et valide les CGU."""

    accept_box = ft.Checkbox(label=t("cgu_accept_checkbox"), value=False)

    def confirm(e):
        if not accept_box.value:
            snack(page, t("cgu_must_accept"), error=True)
            return
        on_accept()

    return ft.View(
        route="/cgu",
        bgcolor=COLORS["bg"],
        padding=20,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text(t("cgu_title"), color="#FFFFFF"),
            bgcolor=COLORS["primary"],
            leading=ft.IconButton(
                ft.icons.ARROW_BACK,
                icon_color="#FFFFFF",
                on_click=lambda e: page.go("/register"),
            ),
        ),
        controls=[
            ft.Container(
                bgcolor="#FFFFFF",
                border_radius=14,
                padding=16,
                content=ft.Text(t("cgu_body"), size=13, color=COLORS["text"]),
            ),
            ft.Container(height=12),
            accept_box,
            ft.Container(height=8),
            primary_button(
                t("create_account_button"), confirm, ft.icons.CHECK_CIRCLE, expand=True
            ),
        ],
    )
