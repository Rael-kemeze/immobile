"""Alertes par zone : l'utilisateur choisit Pays/Ville/Zone et sera notifie."""

from __future__ import annotations
import flet as ft
from components.widgets import CountryCitySelector, primary_button, snack, text_field
from services.auth import Session
from services.config import COLORS
from services.countries import get_country, label
from services.db import db
from services.i18n import t

def _appbar(page: ft.Page) -> ft.AppBar:
    return ft.AppBar(
        title=ft.Text(t("alerts_title"), color="#FFFFFF"),
        bgcolor=COLORS["primary"],
        leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/settings")),
    )

def alerts_view(page: ft.Page) -> ft.View:
    if not Session.user:
        page.go("/login")
        return ft.View(route="/alerts")

    geo = CountryCitySelector(page, Session.user.get("country_code"), Session.user.get("city"))
    zone_field = text_field(t("zone_label"))
    alerts_list = ft.Column(spacing=8)

    def refresh_list():
        rows = db.list_alerts(Session.user["id"])
        if not rows:
            alerts_list.controls = [ft.Container(padding=20, alignment=ft.alignment.center, content=ft.Text(t("no_alerts"), color=COLORS["muted"], text_align=ft.TextAlign.CENTER))]
        else:
            alerts_list.controls = [
                ft.Container(
                    bgcolor="#FFFFFF", border_radius=12, padding=12, border=ft.border.all(1, "#E0E4E1"),
                    content=ft.Row(controls=[
                        ft.Column(expand=True, spacing=2, controls=[
                            ft.Text(label(get_country(a.get("country"))), weight=ft.FontWeight.W_600, size=13),
                            ft.Text(f"{a.get('city')} - {a.get('zone')}", size=12, color=COLORS["muted"]),
                        ]),
                        ft.IconButton(ft.icons.DELETE_OUTLINE, icon_color=COLORS["danger"], tooltip=t("delete_alert"), on_click=lambda e, aid=a["id"]: delete_alert(aid)),
                    ]),
                ) for a in rows
            ]
        page.update()

    def delete_alert(alert_id):
        db.delete_alert(alert_id)
        snack(page, "Alerte supprimée")
        refresh_list()

    def create_alert(e):
        if not geo.city:
            snack(page, t("city_required"), error=True)
            return
        if not (zone_field.value or "").strip():
            snack(page, t("zone_required"), error=True)
            return
        try:
            db.create_alert(Session.user["id"], geo.country_code, geo.city, zone_field.value.strip())
            snack(page, "Alerte créée ! Vous serez notifié pour cette zone")
            zone_field.value = ""
            refresh_list()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)

    refresh_list()

    form = ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=12, controls=[
            ft.Text("Créer une alerte", weight=ft.FontWeight.BOLD, size=16),
            ft.Text("Soyez notifié dès qu'un bien est publié dans votre zone", size=12, color=COLORS["muted"]),
            *geo.controls,
            zone_field,
            primary_button("Créer l'alerte", create_alert, ft.icons.NOTIFICATIONS_ACTIVE, expand=True),
        ])
    )

    return ft.View(
        route="/alerts",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=_appbar(page),
        controls=[
            form,
            ft.Container(height=16),
            ft.Text("Mes alertes actives", weight=ft.FontWeight.BOLD, size=15),
            alerts_list,
            ft.Container(height=30),
        ],
    )
