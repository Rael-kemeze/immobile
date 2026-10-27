"""Liste des pays supportés par l'apllication IMMOBILE."""

from __future__ import annotations
from typing import Dict, List, Optional
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons


FLAG_BASE_URL = "https://flagcdn.com/w40/{code}.png"
FLAG_BASE_URL_HD = "https://flagcdn.com/w80/{code}.png"

def flag_url(code: str, hd: bool = False) -> str:
    if not code:
        return ""
    c = code.strip().lower()
    template = FLAG_BASE_URL_HD if hd else FLAG_BASE_URL
    return template.format(code=c)

def flag_image(code: str, size: int = 22, rounded: bool = True) -> ft.Control:
    if not code:
        code = "CM"
    url = flag_url(code)
    return ft.Container(
        width=size * 1.33, height=size, border_radius=3 if rounded else 0,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Image(src=url, width=size * 1.33, height=size, fit=ft.ImageFit.COVER,
            error_content=ft.Container(width=size * 1.33, height=size, bgcolor="#E0E0E0", alignment=ft.alignment.center,
                content=ft.Text(code.upper()[:2], size=10, weight=ft.FontWeight.BOLD))),
        border=ft.border.all(0.5, "#E0E4E1"),
    )

def flag_row(code: str, text: str, size: int = 20, spacing: int = 8) -> ft.Row:
    return ft.Row(spacing=spacing, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[flag_image(code, size=size), ft.Text(text, size=13, no_wrap=True)])

_RAW = [
    ("CM","Cameroun","Cameroon","+237"),("CI","Côte d'Ivoire","Ivory Coast","+225"),
    ("SN","Sénégal","Senegal","+221"),("ML","Mali","Mali","+223"),
    ("BF","Burkina Faso","Burkina Faso","+226"),("TG","Togo","Togo","+228"),
    ("BJ","Bénin","Benin","+229"),("NE","Niger","Niger","+227"),
    ("GN","Guinée","Guinea","+224"),("GA","Gabon","Gabon","+241"),
    ("CG","Congo","Congo","+242"),("CD","RD Congo","DR Congo","+243"),
    ("TD","Tchad","Chad","+235"),("MG","Madagascar","Madagascar","+261"),
    ("RW","Rwanda","Rwanda","+250"),("NG","Nigeria","Nigeria","+234"),
    ("GH","Ghana","Ghana","+233"),("KE","Kenya","Kenya","+254"),
    ("UG","Ouganda","Uganda","+256"),("TZ","Tanzanie","Tanzania","+255"),
    ("ZA","Afrique du Sud","South Africa","+27"),("MA","Maroc","Morocco","+212"),
    ("DZ","Algérie","Algeria","+213"),("TN","Tunisie","Tunisia","+216"),
    ("FR","France","France","+33"),
]

COUNTRIES: List[Dict[str, str]] = [
    {"code": c, "name": fr, "name_en": en, "dial": dial, "flag_url": flag_url(c), "flag_url_hd": flag_url(c, hd=True), "flag": ""}
    for c, fr, en, dial in _RAW
]

DEFAULT_COUNTRY_CODE = "CM"

def get_country(code: Optional[str]) -> Dict[str, str]:
    return next((c for c in COUNTRIES if c["code"] == code), COUNTRIES[0])

def get_dial(code: Optional[str]) -> str:
    return get_country(code)["dial"]

def country_name(country: Dict[str, str]) -> str:
    try:
        from services.i18n import get_lang
        return country["name_en"] if get_lang() == "en" else country["name"]
    except:
        return country["name"]

def label(country: Dict[str, str]) -> str:
    return f"{country_name(country)} ({country['dial']})"

def code_from_label(text: str) -> Optional[str]:
    for c in COUNTRIES:
        if label(c) == text:
            return c["code"]
    return None
