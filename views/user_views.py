"""Favoris, Mes annonces avec bouton Modifier, Profil, Notifications."""

from __future__ import annotations
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons

from components.widgets import (
    PLACEHOLDER,
    ImagePicker,
    avatar,
    badge,
    image_kwargs,
    bien_card,
    empty_state,
    format_prix,
    outline_button,
    snack,
    text_field,
)
from services.auth import Session
from services.auth_service import clear_session
from services.config import APP_CONFIG, COLORS, STATUS_EN_ATTENTE
from services.db import db
from services.i18n import t
from views.home_view import bottom_bar, reset_home_state


def _appbar(title: str, page: ft.Page, actions=None):
    return ft.AppBar(
        title=ft.Text(title, color="#FFFFFF"),
        bgcolor=COLORS["primary"],
        leading=ft.IconButton(
            FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/home")
        ),
        actions=actions or [],
    )


def favoris_view(page: ft.Page) -> ft.View:
    biens = db.list_favoris(Session.user["id"]) if Session.user else []
    controls = (
        [
            bien_card(
                page,
                b,
                lambda x: page.go(f"/bien/{x['id']}"),
                lambda: page.go("/favoris"),
            )
            for b in biens
        ]
        if biens
        else [empty_state(t("no_favorites"), FT_ICONS.FAVORITE_BORDER)]
    )
    return ft.View(
        route="/favoris",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=_appbar(t("favorites_title"), page),
        controls=controls,
        navigation_bar=bottom_bar(page, 1),
    )


def mes_annonces_view(page: ft.Page) -> ft.View:
    biens = (
        db.list_biens(only_active=False, user_id=Session.user["id"])
        if Session.user else []
    )
    rows = []
    for b in biens:
        photos = b.get("photos") or [PLACEHOLDER]
        statut = b.get("status", "")
        color = COLORS["accent"] if statut == STATUS_EN_ATTENTE else COLORS["primary"]

        def delete(e, bid=b["id"]):
            db.delete_bien(bid)
            snack(page, t("listing_deleted"))
            page.go("/mes-annonces")

        def edit(e, bid=b["id"]):
            page.go(f"/edit/{bid}")

        rows.append(
            ft.Container(
                bgcolor="#FFFFFF",
                border_radius=14,
                padding=10,
                margin=ft.margin.only(bottom=10),
                content=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Container(
                            content=ft.Image(
                                **image_kwargs(photos[0]), width=70, height=70, fit=ft.ImageFit.COVER
                            ),
                            border_radius=10,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            on_click=lambda e, bid=b["id"]: page.go(f"/bien/{bid}"),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=3,
                            controls=[
                                ft.Text(b.get("titre", ""), weight=ft.FontWeight.W_600),
                                ft.Text(format_prix(b), size=12, color=COLORS["muted"]),
                                badge(
                                    t(f"status_{statut}") if statut else "",
                                    color,
                                    "#FFFFFF",
                                ),
                            ],
                        ),
                        ft.Column(spacing=2, controls=[
                            ft.IconButton(
                                FT_ICONS.EDIT_OUTLINED,
                                icon_color=COLORS["primary"],
                                tooltip="Modifier",
                                on_click=edit,
                            ),
                            ft.IconButton(
                                FT_ICONS.DELETE_OUTLINE,
                                icon_color=COLORS["danger"],
                                tooltip="Supprimer",
                                on_click=delete,
                            ),
                        ]),
                    ],
                ),
            )
        )

    return ft.View(
        route="/mes-annonces",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=_appbar(t("my_listings_title"), page),
        controls=rows or [empty_state(t("no_listings"), FT_ICONS.LIST_ALT)],
        floating_action_button=ft.FloatingActionButton(
            icon=FT_ICONS.ADD, bgcolor=COLORS["accent"], on_click=lambda e: page.go("/publish")
        ),
        navigation_bar=bottom_bar(page, 2),
    )


def _current_user():
    u = Session.user
    if u:
        fresh = db.get_user(u["id"])
        if fresh:
            Session.user = fresh
            u = fresh
    return u


def profile_view(page: ft.Page) -> ft.View:
    user = _current_user() or {}
    username = text_field(t("name_label"), value=user.get("username", ""))
    city = text_field(t("city_label"), value=user.get("city", ""))
    locality = text_field(t("zone_label"), value=user.get("locality", ""))

    avatar_box = ft.Container(content=avatar(user, 96))
    photo_btn = ft.OutlinedButton(icon=FT_ICONS.ADD_A_PHOTO_OUTLINED)
    remove_btn = ft.TextButton(
        t("remove_photo"),
        icon=FT_ICONS.DELETE_OUTLINE,
        style=ft.ButtonStyle(color=COLORS["danger"]),
    )

    def refresh_photo_ui():
        u = _current_user() or {}
        avatar_box.content = avatar(u, 96)
        has_photo = bool(u.get("profile_photo_url"))
        photo_btn.text = t("change_photo") if has_photo else t("add_profile_photo")
        remove_btn.visible = has_photo

    def set_photo(url):
        db.update_user(user["id"], {"profile_photo_url": url})
        refresh_photo_ui()
        snack(page, t("photo_updated") if url else t("photo_removed"))
        page.update()

    def on_files(paths):
        snack(page, t("photo_received"))
        try:
            set_photo(db.upload_photo(paths[0]))
        except Exception as ex:
            print(f"[PHOTO] echec profil : {ex!r}")
            snack(page, t("upload_failed", err=ex), error=True)

    picker = ImagePicker(page, "profile", on_files, multiple=False)
    photo_btn.on_click = picker.open
    remove_btn.on_click = lambda e: set_photo(None)
    refresh_photo_ui()

    def save(e):
        db.update_user(
            user["id"],
            {
                "username": (username.value or "").strip(),
                "city": (city.value or "").strip(),
                "locality": (locality.value or "").strip(),
            },
        )
        _current_user()
        snack(page, t("profile_updated"))

    def logout(e):
        clear_session(page)
        Session.logout()
        reset_home_state()
        page.go("/login")

    def go_settings(e):
        page.go("/settings")

    def go_alerts(e):
        page.go("/alerts")

    content = ft.Column(
        spacing=12,
        controls=[
            ft.Row(spacing=12, controls=[avatar_box, ft.Column(controls=[photo_btn, remove_btn], spacing=6)]),
            username,
            city,
            locality,
            ft.ElevatedButton(t("save_button"), on_click=save, style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF")),
            ft.Divider(height=1),
            ft.Container(
                bgcolor="#FFFFFF", border_radius=14, padding=8, border=ft.border.all(1, "#E0E4E1"),
                content=ft.Column(spacing=0, controls=[
                    ft.ListTile(
                        leading=ft.Icon(FT_ICONS.SETTINGS, color=COLORS["primary"]),
                        title=ft.Text("Paramètres"),
                        subtitle=ft.Text("Langue, pays, sécurité", size=11, color=COLORS["muted"]),
                        trailing=ft.Icon(FT_ICONS.CHEVRON_RIGHT),
                        on_click=go_settings,
                    ),
                    ft.Divider(height=1),
                    ft.ListTile(
                        leading=ft.Icon(FT_ICONS.NOTIFICATIONS_ACTIVE_OUTLINED, color=COLORS["primary"]),
                        title=ft.Text("Configuration des alertes"),
                        subtitle=ft.Text("Recevoir une alerte par zone", size=11, color=COLORS["muted"]),
                        trailing=ft.Icon(FT_ICONS.CHEVRON_RIGHT),
                        on_click=go_alerts,
                    ),
                    ft.Divider(height=1),
                    ft.ListTile(
                        leading=ft.Icon(FT_ICONS.NOTIFICATIONS_OUTLINED, color=COLORS["primary"]),
                        title=ft.Text("Notifications"),
                        trailing=ft.Icon(FT_ICONS.CHEVRON_RIGHT),
                        on_click=lambda e: page.go("/notifications"),
                    ),
                ])
            ),
            ft.OutlinedButton(t("logout_button"), icon=FT_ICONS.LOGOUT, on_click=logout),
            ft.Container(height=20),
        ],
    )
    return ft.View(
        route="/profile",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text(t("profile_title"), color="#FFFFFF"),
            bgcolor=COLORS["primary"],
            leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/home")),
            actions=[
                ft.IconButton(FT_ICONS.NOTIFICATIONS_ACTIVE_OUTLINED, icon_color="#FFFFFF", tooltip="Alertes", on_click=go_alerts),
                ft.IconButton(FT_ICONS.SETTINGS, icon_color="#FFFFFF", tooltip="Paramètres", on_click=go_settings),
            ],
        ),
        controls=[content],
        navigation_bar=bottom_bar(page, 3),
    )



def notifications_view(page: ft.Page) -> ft.View:
    notifs = db.list_notifications(Session.user["id"]) if Session.user else []
    controls = []
    for n in notifs:
        controls.append(
            ft.Container(
                bgcolor="#FFFFFF",
                border_radius=12,
                padding=12,
                margin=ft.margin.only(bottom=8),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(n.get("message", ""), size=13),
                        ft.Text(n.get("created_at", "")[:16], size=11, color=COLORS["muted"]),
                    ],
                ),
            )
        )
    if notifs:
        db.mark_notifications_read(Session.user["id"])
    return ft.View(
        route="/notifications",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=_appbar(t("notifications_title"), page),
        controls=controls or [empty_state(t("no_notifications"), FT_ICONS.NOTIFICATIONS_NONE)],
        navigation_bar=bottom_bar(page, 0),
    )
