"""Mot de passe oublié - 3 écrans: demande numéro, vérifie OTP WhatsApp, nouveau mot de passe."""

from __future__ import annotations
import flet as ft
from components.widgets import primary_button, snack, text_field
from services.auth import Session
from services.config import APP_CONFIG, COLORS, LANGUAGES
from services.countries import DEFAULT_COUNTRY_CODE, get_dial
from services.i18n import t

try:
    from services.otp_service import send_verification_code, verify_code, generate_code, save_otp, send_code
except ImportError:
    def send_verification_code(phone, username=""):
        print(f"[OTP DEV] Code pour {phone}: 123456")
        return True, f"Code: 123456 (DEV)"
    def verify_code(phone, code):
        return (code == "123456"), "OK dev"
    def generate_code():
        return "123456"
    def save_otp(phone, code):
        return {"code": code}
    def send_code(phone, code, username=""):
        print(f"[OTP DEV] {phone} -> {code}")
        return True

_RESET_DRAFT: dict = {}

def _logo():
    return ft.Column(
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
        controls=[
            ft.Container(width=76, height=76, bgcolor=COLORS["primary"], border_radius=22, alignment=ft.alignment.center,
                content=ft.Icon(ft.icons.HOME_WORK_ROUNDED, size=40, color="#FFFFFF")),
            ft.Text(APP_CONFIG["APP_NAME"], size=28, weight=ft.FontWeight.BOLD, color=COLORS["primary"], text_align=ft.TextAlign.CENTER),
            ft.Text("Récupération de mot de passe", size=13, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
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

def forgot_password_view(page: ft.Page) -> ft.View:
    phone = text_field(t("phone_label"), prefix_icon=ft.icons.PHONE)
    phone.value = get_dial(DEFAULT_COUNTRY_CODE)

    def do_request(e):
        p = (phone.value or "").strip()
        if not p:
            snack(page, "Entre ton numéro", error=True)
            return
        ok, err, username = Session.request_password_reset(p)
        if not ok:
            snack(page, err, error=True)
            return
        # Génère et envoie OTP via WhatsApp
        from services.otp_service import generate_code, save_otp, send_code
        code = generate_code()
        save_otp(p, code)
        sent = send_code(p, code, username or "")
        if not sent:
            # En DEV on continue même si envoi échoue
            from services.config import COLORS
            print(f"[RESET] Code {code} pour {p} (envoi échoué mais on continue en DEV)")
        
        _RESET_DRAFT.clear()
        _RESET_DRAFT.update({"phone": p, "username": username})
        snack(page, f"Code envoyé sur WhatsApp au {p}")
        page.go("/verify-reset-otp")

    content = _auth_container(page, [
        ft.Container(height=10),
        _logo(),
        ft.Container(height=28),
        ft.Text("Entre ton numéro WhatsApp pour recevoir un code de réinitialisation", size=13, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
        ft.Container(height=10),
        phone,
        ft.Container(height=8),
        primary_button("Recevoir le code sur WhatsApp", do_request, ft.icons.SEND, expand=True),
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
            ft.TextButton("Retour connexion", on_click=lambda e: page.go("/login")),
            ft.TextButton("Créer un compte", on_click=lambda e: page.go("/register")),
        ])
    ])

    return ft.View(route="/forgot-password", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])

def verify_reset_otp_view(page: ft.Page) -> ft.View:
    d = _RESET_DRAFT
    if not d:
        page.go("/forgot-password")
        return ft.View(route="/verify-reset-otp", controls=[ft.Text("Aucune demande en cours")])

    phone_display = d.get("phone", "")
    otp_code = text_field("Code à 6 chiffres *", prefix_icon=ft.icons.VERIFIED_USER, keyboard_type=ft.KeyboardType.NUMBER)
    info_text = ft.Text(f"Code envoyé au {phone_display} sur WhatsApp - Valable 5 min", size=12, color=COLORS["muted"], text_align=ft.TextAlign.CENTER)

    def do_verify(e):
        if not otp_code.value.strip():
            snack(page, "Entre le code reçu", error=True)
            return
        is_valid, msg = verify_code(phone_display, otp_code.value.strip())
        if is_valid:
            snack(page, "Code vérifié ! Choisis ton nouveau mot de passe")
            page.go("/reset-password")
        else:
            snack(page, msg, error=True)

    def do_resend(e):
        from services.otp_service import generate_code, save_otp, send_code
        code = generate_code()
        save_otp(phone_display, code)
        send_code(phone_display, code, d.get("username",""))
        snack(page, f"Nouveau code envoyé ! (DEV: {code})")

    inner_form = ft.Container(
        bgcolor="#FFFFFF", border_radius=18, padding=18,
        shadow=ft.BoxShadow(blur_radius=14, color="#1A00000D"),
        content=ft.Column(spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Icon(ft.icons.VERIFIED_USER, size=48, color=COLORS["primary"]),
            ft.Text("Vérifie ton numéro", size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"], text_align=ft.TextAlign.CENTER),
            info_text, otp_code,
            ft.Container(height=4),
            primary_button("Vérifier le code", do_verify, ft.icons.CHECK_CIRCLE, expand=True),
            ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                ft.TextButton("Renvoyer le code", icon=ft.icons.REFRESH, on_click=do_resend),
                ft.TextButton("Changer numéro", on_click=lambda e: page.go("/forgot-password")),
            ])
        ]),
    )

    content = _auth_container(page, [ft.Container(height=10), _logo(), ft.Container(height=20), inner_form])
    return ft.View(route="/verify-reset-otp", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])

def reset_password_view(page: ft.Page) -> ft.View:
    d = _RESET_DRAFT
    if not d:
        page.go("/forgot-password")
        return ft.View(route="/reset-password", controls=[ft.Text("Aucune demande en cours")])

    phone_display = d.get("phone", "")
    new_pwd = text_field("Nouveau mot de passe *", password=True, can_reveal_password=True, prefix_icon=ft.icons.LOCK)
    confirm_pwd = text_field("Confirmer mot de passe *", password=True, can_reveal_password=True, prefix_icon=ft.icons.LOCK)

    def do_reset(e):
        p1 = (new_pwd.value or "").strip()
        p2 = (confirm_pwd.value or "").strip()
        if not p1 or not p2:
            snack(page, "Remplis tous les champs", error=True)
            return
        if p1 != p2:
            snack(page, "Les mots de passe ne correspondent pas", error=True)
            return
        if len(p1) < 4:
            snack(page, "Mot de passe trop court (min 4)", error=True)
            return
        
        ok, err = Session.reset_password(phone_display, p1, p2)
        if not ok:
            snack(page, err, error=True)
            return
        
        _RESET_DRAFT.clear()
        snack(page, "Mot de passe modifié ! Connecte-toi")
        page.go("/login")

    content = _auth_container(page, [
        ft.Container(height=10),
        _logo(),
        ft.Container(height=20),
        ft.Container(
            bgcolor="#FFFFFF", border_radius=18, padding=18,
            shadow=ft.BoxShadow(blur_radius=14, color="#1A00000D"),
            content=ft.Column(spacing=14, controls=[
                ft.Icon(ft.icons.LOCK_RESET, size=48, color=COLORS["primary"]),
                ft.Text("Nouveau mot de passe", size=20, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(f"Pour {phone_display}", size=12, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
                new_pwd, confirm_pwd,
                primary_button("Changer mon mot de passe", do_reset, ft.icons.CHECK, expand=True),
            ])
        )
    ])

    return ft.View(route="/reset-password", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, controls=[content])
