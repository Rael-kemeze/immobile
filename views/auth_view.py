"""Auth view FINAL - 4 pages, MEME design vert, SANS OTP"""
from __future__ import annotations
import re
import flet as ft

try:
    FT_ICONS = ft.Icons
except AttributeError:
    FT_ICONS = ft.icons

from components.widgets import CountryCitySelector, primary_button, outline_button, snack, text_field
from services.auth import Session
from services.auth_service import save_session
from services.config import COLORS, APP_CONFIG, LANGUAGES
from services.countries import DEFAULT_COUNTRY_CODE, get_dial
from services.db import db
from services.i18n import t
from views.cgu import cgu_view

REGISTER_DRAFT: dict = {}

def _logo():
    return ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
        controls=[
            ft.Container(width=76, height=76, bgcolor=COLORS["primary"], border_radius=22,
                alignment=ft.alignment.center,
                content=ft.Icon(FT_ICONS.HOME_WORK_ROUNDED, size=40, color="#FFFFFF")),
            ft.Text(APP_CONFIG["APP_NAME"], size=28, weight=ft.FontWeight.BOLD, color=COLORS["primary"], text_align=ft.TextAlign.CENTER),
            ft.Text(t("app_tagline"), size=13, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
        ],
    )

def auth_container(page, controls):
    inner = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, controls=controls)
    return ft.Container(alignment=ft.alignment.center, expand=True,
        padding=ft.padding.symmetric(horizontal=24, vertical=20),
        content=ft.Container(content=inner, width=520, alignment=ft.alignment.center))

def login_view(page):
    phone = text_field(t("phone_label"), prefix_icon=FT_ICONS.PHONE)
    phone.value = get_dial(DEFAULT_COUNTRY_CODE)
    password = text_field(t("password_label"), password=True, can_reveal_password=True, prefix_icon=FT_ICONS.LOCK)
    def do_login(e):
        user, err = Session.login(phone.value.strip(), password.value or "")
        if err:
            snack(page, err, error=True); return
        save_session(page, user)
        page.go("/home")
    content = auth_container(page, [
        _logo(), ft.Container(height=28),
        phone, password,
        ft.Container(height=8),
        primary_button(t("login_button"), do_login, FT_ICONS.LOGIN, expand=True),
        ft.TextButton(t("no_account"), on_click=lambda e: page.go("/register")),
    ])
    return ft.View(route="/login", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])

def register_view(page):
    current_step = {"value": 1}
    form_data = {"username": "", "email": "", "phone": "", "country_code": DEFAULT_COUNTRY_CODE, "city": "", "locality": "", "password": ""}
    username = text_field("Nom d'utilisateur *", prefix_icon=FT_ICONS.PERSON)
    email = text_field("Email", prefix_icon=FT_ICONS.EMAIL, keyboard_type=ft.KeyboardType.EMAIL)
    phone = text_field("Numéro de téléphone * (ex: 6XXXXXXXX)", prefix_icon=FT_ICONS.PHONE)
    phone.value = get_dial(DEFAULT_COUNTRY_CODE)
    dial_state = {"dial": phone.value}
    locality = text_field("Quartier *", prefix_icon=FT_ICONS.LOCATION_ON)
    password = text_field("Mot de passe *", password=True, can_reveal_password=True, prefix_icon=FT_ICONS.LOCK)
    confirm_password = text_field("Confirmer mot de passe *", password=True, can_reveal_password=True, prefix_icon=FT_ICONS.LOCK)
    def sync_dial(code):
        new_dial = get_dial(code)
        prev_dial = dial_state["dial"]
        current = phone.value or ""
        rest = current[len(prev_dial):] if current.startswith(prev_dial) else ""
        phone.value = new_dial + rest
        dial_state["dial"] = new_dial
        page.update()
    geo = CountryCitySelector(page, DEFAULT_COUNTRY_CODE, on_country=sync_dial)
    progress = ft.ProgressBar(value=0.25, color=COLORS["primary"], bgcolor="#E0E4E1", height=4, border_radius=2)
    step_text = ft.Text("Étape 1/4 : Identité", size=12, color=COLORS["muted"])
    step1 = ft.Column([username, email], spacing=12)
    step2 = ft.Column([ft.Text("Pays", size=12, color=COLORS["muted"]), geo.country_dd, phone], spacing=12, visible=False)
    step3 = ft.Column([geo.city_dd, geo.city_other, locality], spacing=12, visible=False)
    step4 = ft.Column([password, confirm_password], spacing=12, visible=False)
    app_bar_title = ft.Text("Créer un compte", weight=ft.FontWeight.BOLD, color="#FFFFFF", size=19)
    def show_step(n):
        current_step["value"] = n
        progress.value = n / 4
        titles = {1: "Créer un compte", 2: "Pays & Téléphone", 3: "Ville & Quartier", 4: "Mot de passe"}
        steps = {1: "Étape 1/4 : Identité", 2: "Étape 2/4 : Contact", 3: "Étape 3/4 : Localisation", 4: "Étape 4/4 : Sécurité"}
        app_bar_title.value = titles[n]
        step_text.value = steps[n]
        step1.visible = (n == 1); step2.visible = (n == 2); step3.visible = (n == 3); step4.visible = (n == 4)
        back_btn.visible = (n > 1)
        next_btn.text = "Créer mon compte" if n == 4 else "Suivant"
        next_btn.icon = FT_ICONS.CHECK_CIRCLE if n == 4 else FT_ICONS.ARROW_FORWARD
        page.update()
    def validate_current():
        n = current_step["value"]
        if n == 1:
            if not (username.value or "").strip() or len(username.value.strip()) < 3:
                snack(page, "Nom trop court (min 3)", error=True); return False
            if email.value and not re.match(r"[^@]+@[^@]+\.[^@]+", email.value):
                snack(page, "Email invalide", error=True); return False
            form_data["username"] = username.value.strip()
            form_data["email"] = (email.value or "").strip().lower() or None
        elif n == 2:
            if not phone.value or len(phone.value.strip()) < 8:
                snack(page, "Numéro invalide", error=True); return False
            if db.is_phone_taken(phone.value):
                snack(page, "Ce numéro est déjà utilisé", error=True); return False
            form_data["phone"] = phone.value.strip()
            form_data["country_code"] = geo.country_code
        elif n == 3:
            if not geo.city:
                snack(page, t("city_required"), error=True); return False
            if not locality.value.strip():
                snack(page, "Quartier requis", error=True); return False
            form_data["city"] = geo.city
            form_data["locality"] = locality.value.strip()
        elif n == 4:
            if not password.value or not confirm_password.value:
                snack(page, "Mot de passe requis", error=True); return False
            if password.value != confirm_password.value:
                snack(page, t("passwords_mismatch"), error=True); return False
            if len(password.value) < 4:
                snack(page, "Mot de passe trop court", error=True); return False
            form_data["password"] = password.value or ""
        return True
    def go_next(e=None):
        if not validate_current(): return
        if current_step["value"] < 4:
            show_step(current_step["value"] + 1); return
        REGISTER_DRAFT.clear()
        REGISTER_DRAFT.update({"username": form_data["username"], "email": form_data["email"], "country_code": form_data["country_code"], "phone": form_data["phone"], "city": form_data["city"], "locality": form_data["locality"], "password": form_data["password"], "confirm_password": form_data["password"]})
        page.go("/cgu")
    def go_back(e=None):
        if current_step["value"] > 1: show_step(current_step["value"] - 1)
    next_btn = primary_button("Suivant", go_next, FT_ICONS.ARROW_FORWARD, expand=True)
    back_btn = outline_button("Retour", go_back, FT_ICONS.ARROW_BACK)
    back_btn.visible = False
    app_bar = ft.AppBar(leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="white", on_click=lambda e: page.go("/login") if current_step["value"]==1 else go_back()), title=ft.Row([ft.Container(width=34, height=34, bgcolor="#FFFFFF", border_radius=9, alignment=ft.alignment.center, content=ft.Icon(FT_ICONS.HOME_WORK_ROUNDED, size=20, color=COLORS["primary"])), app_bar_title], spacing=10), bgcolor=COLORS["primary"])
    form_card = ft.Container(bgcolor="#FFFFFF", border_radius=16, padding=16, shadow=ft.BoxShadow(blur_radius=10, color="#1A00000D"), content=ft.Column(spacing=12, controls=[ft.Row([step_text]), progress, step1, step2, step3, step4, ft.Container(height=4), ft.Row([back_btn, next_btn], spacing=10)]))
    content = ft.Container(alignment=ft.alignment.top_center, expand=True, bgcolor=COLORS["bg"], padding=ft.padding.symmetric(horizontal=16, vertical=16), content=ft.Column(spacing=0, controls=[form_card, ft.Container(height=16), ft.TextButton("Déjà un compte ? Se connecter", on_click=lambda e: page.go("/login"))], scroll=ft.ScrollMode.AUTO, expand=True))
    return ft.View(route="/register", bgcolor=COLORS["bg"], appbar=app_bar, scroll=ft.ScrollMode.AUTO, controls=[content])

def verify_otp_view(page):
    page.go("/register")
    return ft.View(route="/verify-otp", controls=[ft.Text("Plus de vérification")])

def register_cgu_view(page):
    def finalize():
        d = REGISTER_DRAFT
        if not d:
            page.go("/register"); return
        user, err = Session.register(d["username"], d["phone"], d["password"], d["confirm_password"], d["country_code"], d["city"], d["locality"], email=d.get("email"))
        if err:
            snack(page, err, error=True); page.go("/register"); return
        REGISTER_DRAFT.clear()
        save_session(page, user)
        snack(page, "Bienvenue sur IMMOBILE")
        page.go("/home")
    return cgu_view(page, finalize)