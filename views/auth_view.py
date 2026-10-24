"""Ecrans d'inscription - SANS VERIFICATION (comme demandé)."""

from __future__ import annotations
import flet as ft
from components.widgets import CountryCitySelector, primary_button, snack, text_field
from services.auth import Session
from services.auth_service import save_session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.countries import DEFAULT_COUNTRY_CODE, get_dial
from services.i18n import t
from views.cgu import cgu_view

_REGISTER_DRAFT: dict = {}

def _logo():
    return ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
        controls=[
            ft.Container(width=76, height=76, bgcolor=COLORS["primary"], border_radius=22, alignment=ft.alignment.center,
                content=ft.Icon(ft.icons.HOME_WORK_ROUNDED, size=40, color="#FFFFFF")),
            ft.Text(APP_CONFIG["APP_NAME"], size=28, weight=ft.FontWeight.BOLD, color=COLORS["primary"], text_align=ft.TextAlign.CENTER),
            ft.Text(t("app_tagline"), size=13, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
        ],
    )

def _auth_container(page: ft.Page, controls: list) -> ft.Control:
    inner = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, controls=controls)
    return ft.Container(
        alignment=ft.alignment.center,
        expand=True,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        content=ft.Container(content=inner, width=520, alignment=ft.alignment.center)
    )

def login_view(page: ft.Page) -> ft.View:
    phone = text_field(t("phone_label"), prefix_icon=ft.icons.PHONE)
    phone.value = get_dial(DEFAULT_COUNTRY_CODE)
    password = text_field(t("password_label"), password=True, can_reveal_password=True)

    def do_login(e):
        user, err = Session.login(phone.value.strip(), password.value or "")
        if err:
            snack(page, err, error=True); return
        save_session(page, user)
        page.go("/home")

    content = _auth_container(page, [
        ft.Container(height=10), _logo(), ft.Container(height=28),
        phone, password,
        ft.Row(alignment=ft.MainAxisAlignment.END, controls=[ft.TextButton("Mot de passe oublié ?", on_click=lambda e: page.go("/forgot-password"))]),
        ft.Container(height=8),
        primary_button(t("login_button"), do_login, ft.icons.LOGIN, expand=True),
        ft.TextButton(t("no_account"), on_click=lambda e: page.go("/register")),
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[ft.TextButton(code.upper(), on_click=lambda e, c=code: page.go(f"/lang/{c}")) for code in LANGUAGES]),
    ])
    return ft.View(route="/login", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])

def register_view(page: ft.Page) -> ft.View:
    username = text_field(t("name_label"), prefix_icon=ft.icons.PERSON)
    email = text_field(t("email_label"), prefix_icon=ft.icons.EMAIL, keyboard_type=ft.KeyboardType.EMAIL)
    phone = text_field(t("phone_label"), prefix_icon=ft.icons.PHONE)
    phone.value = get_dial(DEFAULT_COUNTRY_CODE)
    dial_state = {"dial": phone.value}
    locality = text_field(t("zone_label"))
    password = text_field(t("password_label"), password=True, can_reveal_password=True)
    confirm_password = text_field(t("confirm_password_label"), password=True, can_reveal_password=True)

    def sync_dial(code: str):
        new_dial = get_dial(code)
        prev_dial = dial_state["dial"]
        current = phone.value or ""
        rest = current[len(prev_dial):] if current.startswith(prev_dial) else ""
        phone.value = new_dial + rest
        dial_state["dial"] = new_dial

    geo = CountryCitySelector(page, DEFAULT_COUNTRY_CODE, on_country=sync_dial)

    def go_to_cgu(e):
        if not (username.value or "").strip():
            snack(page, t("name_too_short"), error=True); return
        if (password.value or "") != (confirm_password.value or ""):
            snack(page, t("passwords_mismatch"), error=True); return
        if not geo.city:
            snack(page, t("city_required"), error=True); return
        from services.db import db
        if db.is_phone_taken(phone.value):
            snack(page, "Ce numéro est déjà utilisé", error=True); return
        _REGISTER_DRAFT.clear()
        _REGISTER_DRAFT.update({
            "username": (username.value or "").strip(),
            "email": (email.value or "").strip().lower() or None,
            "country_code": geo.country_code,
            "phone": (phone.value or "").strip(),
            "city": geo.city,
            "locality": (locality.value or "").strip(),
            "password": password.value or "",
            "confirm_password": confirm_password.value or "",
        })
        page.go("/cgu")

    form = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=18,
        shadow=ft.BoxShadow(blur_radius=14, color="#1A00000D"),
        content=ft.Column(spacing=10, controls=[
            username, email, geo.country_dd, phone, geo.city_dd, geo.city_other, locality, password, confirm_password,
        ]),
    )

    content = _auth_container(page, [
        ft.Container(height=20), _logo(), ft.Container(height=20), form, ft.Container(height=14),
        primary_button(t("continue_button"), go_to_cgu, ft.icons.ARROW_FORWARD, expand=True),
        ft.TextButton(t("has_account"), on_click=lambda e: page.go("/login")),
    ])
    return ft.View(route="/register", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])

def verify_otp_view(page: ft.Page) -> ft.View:
    """Plus utilisée - redirige vers register"""
    page.go("/register")
    return ft.View(route="/verify-otp", controls=[ft.Text("Plus de vérification")])

def register_cgu_view(page: ft.Page) -> ft.View:
    """SANS VERIFICATION - Crée compte direct après CGU"""
    def finalize():
        d = _REGISTER_DRAFT
        if not d:
            page.go("/register"); return
        
        # CRÉATION DIRECTE SANS OTP - comme demandé
        user, err = Session.register(
            d["username"], d["phone"], d["password"], d["confirm_password"],
            d["country_code"], d["city"], d["locality"], email=d.get("email")
        )
        if err:
            snack(page, err, error=True)
            page.go("/register")
            return
        
        _REGISTER_DRAFT.clear()
        save_session(page, user)
        snack(page, "Bienvenue sur IMMOBILE")
        page.go("/home")
    
    return cgu_view(page, finalize)
