"""Composants UI réutilisables - version avec les drapeaux + RESPONSIVE."""

from __future__ import annotations
import base64, os, shutil, sys, traceback
from pathlib import Path as PPath
from typing import Any, Callable, Dict, List, Optional, Union
import flet as ft

from services.auth import Session
from services.auth_service import save_session
from services.config import APP_CONFIG, COLORS, OTHER_CITY, ROLE_SUPER_ADMIN, get_cities, get_currency
from services.countries import COUNTRIES, DEFAULT_COUNTRY_CODE, get_country, flag_image, flag_url, label
from services.db import ASSETS_DIR, WEB_UPLOAD_DIR, db
from services.monetization import monetization
from services.i18n import t
# FIX COMPAT Flet 0.27 vs 0.28
try:
    FT_ICONS = ft.Icons
except AttributeError:
    FT_ICONS = ft.icons

PLACEHOLDER = "https://placehold.co/600x400/0F6B3F/FFFFFF/png?text=IMMOBILE"
_B64_CACHE: Dict[Any, str] = {}

def image_kwargs(src: Optional[str]) -> Dict[str, str]:
    if not src:
        return {"src": PLACEHOLDER}
    if src.startswith(("http://", "https://", "data:")):
        return {"src": src}
    path = PPath(src)
    if not path.is_absolute():
        path = ASSETS_DIR / src
    try:
        st = path.stat()
        key = (str(path), st.st_mtime_ns, st.st_size)
        if key not in _B64_CACHE:
            if len(_B64_CACHE) > 80:
                _B64_CACHE.pop(next(iter(_B64_CACHE)))
            _B64_CACHE[key] = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"src_base64": _B64_CACHE[key]}
    except OSError:
        print(f"[PHOTO] fichier introuvable : {path}")
        return {"src": src}

def format_prix(bien: Dict[str, Any]) -> str:
    if bien.get("prix_sur_place"):
        return t("price_on_site")
    prix = bien.get("prix")
    if not prix:
        return t("price_not_specified")
    try:
        montant = f"{int(prix):,}".replace(",", " ")
    except:
        montant = str(prix)
    suffix = t("negotiable_suffix") if bien.get("prix_discutable") else ""
    devise = bien.get("devise") or get_currency(bien.get("country_code"))
    return f"{montant} {devise}{suffix}"

def type_label(bien: Dict[str, Any]) -> str:
    raw = bien.get("type_bien") or ""
    key = f"type_{raw}"
    txt = t(key)
    return txt if txt != key else raw.replace("_", " ").title()

def wa_url(numero: str, bien: Dict[str, Any] = None) -> str:
    clean = "".join(ch for ch in (numero or "") if ch.isdigit())
    if bien:
        titre = bien.get("titre","").strip()
        city = bien.get("city","")
        prix_txt = format_prix(bien)
        # Message pré-rempli venant de l'app
        msg = f"Bonjour, je vous contacte depuis l'application IMMOBILE pour votre annonce '{titre}' à {city}. Prix: {prix_txt}. Je suis intéressé(e). Pouvez-vous me donner plus d'infos ?"
        # URL encode
        import urllib.parse
        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{clean}?text={encoded}"
    return f"https://wa.me/{clean}"

def call_url(numero: str) -> str:
    clean = "".join(ch for ch in (numero or "") if ch.isdigit() or ch in "+")
    # Garde le + si présent
    if not clean.startswith("+"):
        # Ajoute indicatif si numéro camerounais sans +
        if len(clean) >= 9:
            clean = f"+237{clean[-9:]}" if not clean.startswith("237") else f"+{clean}"
    return f"tel:{clean}"

def primary_button(text: str, on_click, icon: Optional[str]=None, expand=False):
    return ft.ElevatedButton(text, icon=icon, on_click=on_click, expand=expand, height=48,
        style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)))

def outline_button(text: str, on_click, icon: Optional[str]=None, expand=False):
    return ft.OutlinedButton(text, icon=icon, on_click=on_click, expand=expand, height=48,
        style=ft.ButtonStyle(color=COLORS["primary"], shape=ft.RoundedRectangleBorder(radius=12), side=ft.BorderSide(1.2, COLORS["primary"])))

def whatsapp_button(page: ft.Page, numero: str, expand: bool=True, label: str = None, bien: Dict[str, Any] = None):
    txt_label = label or t("whatsapp_contact")
    url = wa_url(numero, bien)
    return ft.ElevatedButton(txt_label, icon=FT_ICONS.CHAT, expand=expand, height=46,
        on_click=lambda e: page.launch_url(url),
        style=ft.ButtonStyle(bgcolor="#25D366", color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)))

def call_button(page: ft.Page, numero: str, expand: bool=False):
    return ft.ElevatedButton(f"Appeler {numero}", icon=FT_ICONS.CALL, expand=expand, height=46,
        on_click=lambda e: page.launch_url(call_url(numero)),
        style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)))

def phone_row(page: ft.Page, numero: str, label: str, bien: Dict[str, Any] = None):
    """Affiche numero avec boutons Appeler et WhatsApp"""
    return ft.Container(
        bgcolor="#F6F8F7", border_radius=12, padding=10, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=6, controls=[
                ft.Icon(FT_ICONS.PHONE, size=18, color=COLORS["primary"]),
                ft.Text(label, size=12, color=COLORS["muted"], weight=ft.FontWeight.W_600),
                ft.Text(numero, size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ]),
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, content=ft.ElevatedButton("Appeler", icon=FT_ICONS.CALL, expand=True, height=40,
                    on_click=lambda e: page.launch_url(call_url(numero)),
                    style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=10)))),
                ft.Container(expand=True, content=whatsapp_button(page, numero, expand=True, label="WhatsApp", bien=bien)),
            ]),
        ])
    )


def text_field(label: str, **kwargs) -> ft.TextField:
    return ft.TextField(label=label, border_radius=12, filled=True, bgcolor="#FFFFFF", border_color="#DDE4DF", focused_border_color=COLORS["primary"], **kwargs)

def badge(text: str, bg: str, color: str="#FFFFFF"):
    return ft.Container(content=ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=color), bgcolor=bg, padding=ft.padding.symmetric(4,9), border_radius=20)

# ---------- RESPONSIVE HELPERS ----------
def responsive_wrapper(content: ft.Control, max_width: int = 1200, padding: int = 12) -> ft.Control:
    return ft.Container(
        alignment=ft.alignment.top_center,
        expand=True,
        padding=ft.padding.symmetric(horizontal=padding, vertical=0),
        content=ft.Container(content=content, width=max_width, alignment=ft.alignment.top_center)
    )

def auth_wrapper(content: ft.Control) -> ft.Control:
    return ft.Container(alignment=ft.alignment.center, expand=True, content=ft.Container(content=content, width=520, alignment=ft.alignment.center))

def is_desktop(page: ft.Page) -> bool:
    try:
        return (page.window_width or 0) >= 900
    except:
        return False

def app_bar(title: str, page: ft.Page, actions=None, show_back: bool=False):
    logo_widget = ft.Container(width=34, height=34, bgcolor="#FFFFFF", border_radius=9, alignment=ft.alignment.center,
        content=ft.Icon(FT_ICONS.HOME_WORK_ROUNDED, size=20, color=COLORS["primary"]))
    title_widget = ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[logo_widget, ft.Text(title, weight=ft.FontWeight.BOLD, color="#FFFFFF", size=19)])

    def _safe_back(e):
        try:
            if len(page.views) > 1:
                page.views.pop()
                page.update()
                return
        except Exception as ex:
            print(f"[NAV] back error: {ex}")
        page.go("/home")

    return ft.AppBar(
        leading=(ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="white", on_click=_safe_back) if show_back else None),
        title=title_widget, bgcolor=COLORS["primary"], center_title=False, actions=actions or [])

def avatar(user: Dict[str, Any], size: int=42):
    photo = user.get("profile_photo_url") or user.get("photo") or user.get("avatar")
    if photo:
        try:
            kwargs = image_kwargs(photo)
            return ft.Container(width=size, height=size, border_radius=size//2, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=ft.Image(**kwargs, width=size, height=size, fit=ft.ImageFit.COVER))
        except Exception as ex:
            print(f"[AVATAR] erreur affichage photo {photo}: {ex}")
            return ft.CircleAvatar(foreground_image_src=photo, radius=size//2)
    initials = (user.get("username","?")[:2]).upper()
    return ft.CircleAvatar(content=ft.Text(initials, size=size//3), bgcolor=COLORS["primary"], color="#FFFFFF", radius=size//2)

def stat_card(icon, label, value, color):
    return ft.Container(expand=True, bgcolor="#FFFFFF", border_radius=14, padding=12, border=ft.border.all(1,"#E0E4E1"),
        content=ft.Column(spacing=2, controls=[
            ft.Icon(icon, color=color, size=26),
            ft.Text(str(value), size=28, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Text(label, size=12, color=COLORS["muted"]),
        ]))

def snack(page: ft.Page, message: str, error: bool=False):
    page.snack_bar = ft.SnackBar(content=ft.Text(message, color="#FFFFFF"), bgcolor=COLORS["danger"] if error else COLORS["primary"])
    page.snack_bar.open = True
    page.update()

def skeleton_card() -> ft.Container:
    def block(height: int, width: Any = None, radius: int = 8):
        return ft.Container(height=height, width=width, bgcolor="#E4E9E6", border_radius=radius, animate_opacity=800, opacity=0.6)
    return ft.Container(bgcolor=COLORS["card"] if "card" in COLORS else "#FFFFFF", border_radius=16, margin=ft.margin.only(bottom=14), shadow=ft.BoxShadow(blur_radius=10, color="#1A00000D"),
        content=ft.Column(spacing=10, controls=[
            block(170, radius=0),
            ft.Container(padding=12, content=ft.Column(spacing=8, controls=[block(18, 120), block(14, 200), block(12, 140)])),
        ]))

def empty_state(message: str, icon=None):
    if icon is None:
        icon = FT_ICONS.SEARCH_OFF
    return ft.Container(alignment=ft.alignment.center, padding=40,
        content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, controls=[
            ft.Icon(icon, size=54, color=COLORS["muted"]),
            ft.Text(message, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
        ]))

def password_card(page: ft.Page, title: Optional[str] = None) -> ft.Container:
    current = text_field(t("current_password_label"), password=True, can_reveal_password=True)
    new = text_field(t("new_password_label"), password=True, can_reveal_password=True)
    confirm = text_field(t("confirm_new_password_label"), password=True, can_reveal_password=True)
    def submit(e):
        ok, err = Session.change_password(current.value or "", new.value or "", confirm.value or "")
        if not ok:
            snack(page, err, error=True)
            return
        snack(page, t("profile_updated"))
        current.value = new.value = confirm.value = ""
        page.update()
    return ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=12, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=10, controls=[
            ft.Text(title or t("change_password"), weight=ft.FontWeight.BOLD),
            current, new, confirm,
            primary_button(t("save_button"), submit, FT_ICONS.SAVE, expand=True),
        ]))

_PICKERS: Dict[str, Any] = {}

class ImagePicker:
    def __init__(self, page: ft.Page, key: str, on_files: Callable[[List[str]], None], multiple: bool=False, limit: Union[int, Callable[[], int], None]=None, on_overflow: Optional[Callable[[], None]]=None):
        self.page = page
        self.on_files = on_files
        self.on_overflow = on_overflow
        self.multiple = multiple
        self.limit = limit
        self.picker = ft.FilePicker(on_result=self._on_result, on_upload=self._on_upload)
        old = _PICKERS.get(key)
        if old is not None and old in page.overlay:
            page.overlay.remove(old)
        page.overlay.append(self.picker)
        _PICKERS[key] = self.picker

    def open(self, e=None):
        if (sys.platform.startswith("linux") and not getattr(self.page, "web", False) and not any(shutil.which(x) for x in ("zenity", "kdialog", "qarma"))):
            snack(self.page, t("picker_no_tool"), error=True)
        self.picker.pick_files(allow_multiple=self.multiple, file_type=ft.FilePickerFileType.IMAGE)

    def _deliver(self, paths: List[str]):
        try:
            self.on_files(paths)
        except Exception as ex:
            traceback.print_exc()
            snack(self.page, t("upload_failed", err=ex), error=True)

    def _max(self) -> Optional[int]:
        return self.limit() if callable(self.limit) else self.limit

    def _on_result(self, e):
        if not e.files:
            return
        files = list(e.files)
        cap = self._max()
        if cap is not None:
            if len(files) > cap and self.on_overflow:
                self.on_overflow()
            files = files[:max(cap, 0)]
        local = [f.path for f in files if getattr(f, "path", None)]
        if local:
            self._deliver(local)
        web = [f for f in files if not getattr(f, "path", None)]
        if web:
            self.picker.upload([ft.FilePickerUploadFile(f.name, upload_url=self.page.get_upload_url(f.name, 600)) for f in web])

    def _on_upload(self, e):
        if getattr(e, "error", None):
            snack(self.page, t("upload_failed", err=e.error), error=True)
            return
        if e.progress == 1:
            self._deliver([os.path.join(str(WEB_UPLOAD_DIR), e.file_name)])

def admin_actions(page: ft.Page, bien: Dict[str, Any], on_changed: Optional[Callable]=None):
    if not Session.is_admin():
        return None
    def ask(message: str, confirm_text: str, action: Callable):
        dlg = ft.AlertDialog(modal=True, content=ft.Text(message))
        def close(e=None):
            dlg.open = False
            page.update()
        def confirm(e):
            close()
            action()
        dlg.actions = [ft.TextButton(t("cancel_button"), on_click=close), ft.TextButton(confirm_text, on_click=confirm, style=ft.ButtonStyle(color=COLORS["danger"]))]
        page.dialog = dlg
        dlg.open = True
        page.update()
    def do_delete():
        db.delete_bien(bien["id"])
        snack(page, t("listing_deleted"))
        if on_changed:
            on_changed()
    def do_block():
        owner = db.get_user(bien.get("user_id"))
        if not owner:
            return
        if owner.get("role") == ROLE_SUPER_ADMIN:
            snack(page, t("cannot_block_admin"), error=True)
            return
        db.update_user(owner["id"], {"is_blocked": True})
        snack(page, t("user_blocked"))
        if on_changed:
            on_changed()
    return ft.Row(spacing=8, controls=[
        ft.Container(expand=True, content=ft.OutlinedButton(t("delete_button"), icon=FT_ICONS.DELETE_OUTLINE, on_click=lambda e: ask(t("confirm_delete_listing"), t("delete_button"), do_delete), style=ft.ButtonStyle(color=COLORS["danger"], side=ft.BorderSide(1, COLORS["danger"])))),
        ft.Container(expand=True, content=ft.OutlinedButton(t("block_button"), icon=FT_ICONS.BLOCK, on_click=lambda e: ask(t("confirm_block_user"), t("block_button"), do_block), style=ft.ButtonStyle(color=COLORS["danger"], side=ft.BorderSide(1, COLORS["danger"])))),
    ])

class CountryCitySelector:
    def __init__(self, page: ft.Page, country_code: Optional[str]=None, city: Optional[str]=None, on_country: Optional[Callable[[str], None]]=None):
        self.page = page
        self.on_country_cb = on_country
        self.city_other = text_field("Autre ville", visible=False)
        self.country_dd = ft.Dropdown(
            label=t("country_label"), value=country_code or DEFAULT_COUNTRY_CODE,
            options=[
                ft.dropdown.Option(key=c["code"], content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Image(src=c["flag_url"], width=24, height=18, fit=ft.ImageFit.COVER, border_radius=2),
                    ft.Text(f"{c['name']} ({c['dial']})", size=13)
                ])) for c in COUNTRIES
            ],
            on_change=self._on_country, border_radius=12, filled=True, bgcolor="#FFFFFF"
        )
        self.city_dd = ft.Dropdown(label=t("city_label"), options=[], border_radius=12, filled=True, bgcolor="#FFFFFF", on_change=self._on_city)
        self._fill(city)
        self.controls = [self.country_dd, self.city_dd, self.city_other]
    def _fill(self, selected_city: Optional[str]=None):
        code = self.country_dd.value or DEFAULT_COUNTRY_CODE
        cities = get_cities(code)
        self.city_dd.options = [ft.dropdown.Option(c) for c in cities]
        if selected_city and selected_city in cities:
            self.city_dd.value = selected_city
        elif cities:
            self.city_dd.value = cities[0]
        else:
            self.city_dd.value = ""
        self.city_other.visible = (self.city_dd.value == OTHER_CITY)
    def _on_country(self, e):
        self._fill()
        if self.on_country_cb:
            self.on_country_cb(self.country_dd.value)
        self.page.update()
    def _on_city(self, e):
        self.city_other.visible = self.city_dd.value == OTHER_CITY
        self.page.update()
    @property
    def controls(self):
        return [self.country_dd, self.city_dd, self.city_other]
    @controls.setter
    def controls(self, value):
        self._controls = value
    @property
    def country_code(self) -> str:
        return self.country_dd.value or DEFAULT_COUNTRY_CODE
    @property
    def city(self) -> str:
        if self.city_dd.value == OTHER_CITY:
            return (self.city_other.value or "").strip()
        return (self.city_dd.value or "").strip()

def bien_card(page: ft.Page, bien: Dict[str, Any], on_open: Callable, on_changed: Optional[Callable]=None):
    is_fav = db.is_favori(Session.user["id"], bien["id"]) if Session.user else False
    def toggle_fav(e):
        if not Session.user:
            page.go("/login")
            return
        if is_fav:
            db.remove_favori(Session.user["id"], bien["id"])
        else:
            db.add_favori(Session.user["id"], bien["id"])
        if on_changed:
            on_changed()
    photos = bien.get("photos") or []
    first_photo = photos[0] if photos else None
    
    # Responsive image height - larger on desktop
    is_desktop = (page.window_width or 0) >= 900
    img_h = 200 if is_desktop else 190
    
    return ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=0,
        border=ft.border.all(1, "#E0E4E1"),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        shadow=ft.BoxShadow(blur_radius=8, color="#0F000008"),
        content=ft.Column(spacing=0, controls=[
            ft.Stack(controls=[
                ft.Container(
                    height=img_h,
                    width=float("inf"),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    content=ft.Image(**image_kwargs(first_photo), width=float("inf"), height=img_h, fit=ft.ImageFit.COVER),
                ),
                ft.Container(top=10, left=10, content=ft.Column(spacing=6, controls=[
                    ft.Row(spacing=6, controls=[
                        flag_image(bien.get("country_code","CM"), size=18),
                        badge(type_label(bien), COLORS["primary"])
                    ]),
                    ft.Container(
                        visible=monetization.is_featured(bien),
                        bgcolor="#F59E0B",
                        padding=ft.padding.symmetric(4,8),
                        border_radius=20,
                        content=ft.Row(spacing=4, controls=[
                            ft.Icon(FT_ICONS.ROCKET_LAUNCH, size=12, color="#FFFFFF"),
                            ft.Text("SPONSORISÉ", size=10, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        ])
                    ),
                ])),
                ft.Container(top=10, right=10, content=ft.IconButton(
                    icon=FT_ICONS.FAVORITE if is_fav else FT_ICONS.FAVORITE_BORDER,
                    icon_color="#FF3B30" if is_fav else "#FFFFFF",
                    bgcolor="#00000088", on_click=toggle_fav
                ))
            ]),
            ft.Container(padding=12, content=ft.Column(spacing=6, controls=[
                ft.Text(bien.get("titre",""), weight=ft.FontWeight.BOLD, size=15, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row(spacing=6, controls=[
                    ft.Icon(FT_ICONS.LOCATION_ON_OUTLINED, size=15, color=COLORS["muted"]),
                    flag_image(bien.get("country_code","CM"), size=14),
                    ft.Text(f"{bien.get('city')} - {bien.get('locality')}", size=12, color=COLORS["muted"]),
                ]),
                ft.Text(format_prix(bien), weight=ft.FontWeight.BOLD, size=16, color=COLORS["primary"]),
                ft.Row(spacing=8, controls=[
                    ft.Container(expand=True, content=whatsapp_button(page, bien.get("whatsapp") or bien.get("user_phone") or "", expand=True, bien=bien)),
                    ft.ElevatedButton(t("details_button"), on_click=lambda e: on_open(bien),
                        style=ft.ButtonStyle(bgcolor="#FFFFFF", color=COLORS["primary"], side=ft.BorderSide(1, COLORS["primary"]), shape=ft.RoundedRectangleBorder(radius=12)))
                ])
            ]))
        ])
    )