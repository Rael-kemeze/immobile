"""Ecran Parametres : compte, securite, preferences, infos."""

from __future__ import annotations
import flet as ft
from components.widgets import avatar, badge, password_card, snack, text_field
from services.auth import Session
from services.auth_service import clear_session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.countries import COUNTRIES, get_country, label
from services.i18n import get_lang, set_lang, t
from views.home_view import HOME_COUNTRY_KEY, STATE, reset_home_state

_LANG_NAMES = {"fr": "Francais", "en": "English"}
LANG_OPTIONS = [(code, _LANG_NAMES.get(code, code)) for code in LANGUAGES]

def _card(title: str, controls) -> ft.Container:
    return ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=ft.padding.symmetric(vertical=10, horizontal=6),
        border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=0, controls=[
            ft.Container(padding=ft.padding.only(left=12, top=4, bottom=4), content=ft.Text(title.upper(), size=11, weight=ft.FontWeight.BOLD, color=COLORS["muted"])),
            *controls,
        ]),
    )

def _tile(icon: str, text: str, on_click, color: str = None, subtitle: str = None) -> ft.ListTile:
    return ft.ListTile(
        leading=ft.Icon(icon, color=color or COLORS["primary"]),
        title=ft.Text(text, color=color or COLORS["text"]),
        subtitle=ft.Text(subtitle, size=12) if subtitle else None,
        trailing=ft.Icon(ft.icons.CHEVRON_RIGHT, color=COLORS["muted"]),
        on_click=on_click,
    )

def settings_view(page: ft.Page) -> ft.View:
    user = Session.user or {}
    is_admin = Session.is_admin()

    header = ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Row(spacing=14, controls=[
            avatar(user, 60),
            ft.Column(spacing=2, expand=True, controls=[
                ft.Text(user.get("username", ""), weight=ft.FontWeight.BOLD, size=16),
                ft.Text(user.get("phone", ""), size=13, color=COLORS["muted"]),
                badge(t("role_admin") if is_admin else t("role_user"), COLORS["accent"] if is_admin else COLORS["primary"], "#12211A" if is_admin else "#FFFFFF"),
            ]),
        ]),
    )

    lang_dd = ft.Dropdown(label=t("language_label"), border_radius=12, filled=True, bgcolor="#FFFFFF", options=[ft.dropdown.Option(code, name) for code, name in LANG_OPTIONS], value=get_lang())
    def on_lang(e):
        set_lang(page, lang_dd.value)
        page.go("/settings")
    lang_dd.on_change = on_lang

    try:
        pref = page.client_storage.get(HOME_COUNTRY_KEY)
    except Exception:
        pref = None
    current = pref or (user.get("country_code") or "ALL")
    country_dd = ft.Dropdown(label=t("default_country_label"), border_radius=12, filled=True, bgcolor="#FFFFFF", options=[ft.dropdown.Option("ALL", t("all_countries"))] + [ft.dropdown.Option(c["code"], label(c)) for c in COUNTRIES], value=current)
    def on_country(e):
        code = country_dd.value or "ALL"
        try:
            page.client_storage.set(HOME_COUNTRY_KEY, code)
        except:
            pass
        STATE["country_code"] = None if code == "ALL" else code
        STATE["country_init"] = True
        snack(page, t("default_country_saved"))
    country_dd.on_change = on_country

    def open_dialog(dlg: ft.AlertDialog):
        page.dialog = dlg
        dlg.open = True
        page.update()
    def close_dialog(dlg: ft.AlertDialog):
        dlg.open = False
        page.update()
    def show_terms(e):
        dlg = ft.AlertDialog(title=ft.Text(t("cgu_title")), content=ft.Column([ft.Text(t("cgu_body"), size=13)], scroll=ft.ScrollMode.AUTO, height=320, tight=True))
        dlg.actions = [ft.TextButton(t("close_button"), on_click=lambda e: close_dialog(dlg))]
        open_dialog(dlg)
    def show_about(e):
        dlg = ft.AlertDialog(title=ft.Text(t("about_title")), content=ft.Column([ft.Text(APP_CONFIG["APP_NAME"], weight=ft.FontWeight.BOLD, size=18), ft.Text(f"{t('version_label')} {APP_CONFIG['APP_VERSION']}", size=13), ft.Text(t("about_text"), size=13)], tight=True))
        dlg.actions = [ft.TextButton(t("close_button"), on_click=lambda e: close_dialog(dlg))]
        open_dialog(dlg)
    def ask_delete_account(e):
        pwd = text_field(t("password_label"), password=True, can_reveal_password=True)
        dlg = ft.AlertDialog(modal=True, title=ft.Text(t("delete_account")), content=ft.Column([ft.Text(t("delete_account_warning"), size=13), pwd], tight=True))
        def confirm(ev):
            ok, err = Session.delete_account(pwd.value or "")
            if not ok:
                snack(page, err, error=True)
                return
            close_dialog(dlg)
            clear_session(page)
            reset_home_state()
            snack(page, t("account_deleted"))
            page.go("/login")
        dlg.actions = [ft.TextButton(t("cancel_button"), on_click=lambda e: close_dialog(dlg)), ft.TextButton(t("delete_account"), on_click=confirm, style=ft.ButtonStyle(color=COLORS["danger"]))]
        open_dialog(dlg)
    def logout(e):
        clear_session(page)
        Session.logout()
        reset_home_state()
        page.go("/login")

    account_tiles = [
        _tile(ft.icons.PERSON_OUTLINE, t("edit_profile"), lambda e: page.go("/profile")),
        _tile(ft.icons.NOTIFICATIONS_ACTIVE_OUTLINED, t("my_alerts"), lambda e: page.go("/alerts"), subtitle="Configuration des alertes par zone"),
    ]
    if is_admin:
        account_tiles.insert(0, _tile(ft.icons.ADMIN_PANEL_SETTINGS_OUTLINED, t("admin_space"), lambda e: page.go("/admin"), color=COLORS["accent"]))

    info_tiles = [
        _tile(ft.icons.DESCRIPTION_OUTLINED, t("terms_link"), show_terms),
        _tile(ft.icons.INFO_OUTLINE, t("about_title"), show_about, subtitle=f"{t('version_label')} {APP_CONFIG['APP_VERSION']}"),
        _tile(ft.icons.LOGOUT, t("logout_button"), logout),
    ]

    danger = []
    if not is_admin:
        danger = [_card(t("danger_zone"), [_tile(ft.icons.DELETE_FOREVER_OUTLINED, t("delete_account"), ask_delete_account, color=COLORS["danger"])])]

    def gap():
        return ft.Container(height=12)

    return ft.View(
        route="/settings",
        bgcolor=COLORS["bg"],
        padding=16,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(title=ft.Text(t("settings_title"), color="#FFFFFF"), bgcolor=COLORS["primary"], leading=ft.IconButton(ft.icons.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/profile"))),
        controls=[
            header, gap(),
            _card(t("settings_account"), account_tiles), gap(),
            password_card(page), gap(),
            _card(t("settings_preferences"), [ft.Container(padding=10, content=ft.Column([lang_dd, country_dd], spacing=12))]), gap(),
            _card(t("settings_info"), info_tiles), gap(),
            *danger, ft.Container(height=24),
        ],
    )
