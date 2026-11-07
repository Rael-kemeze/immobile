"""Publication / modification d'une annonce - assistant en 4 etapes.

  1. Photos (galerie uniquement, plus de champ URL)
  2. Le bien : type d'annonce, categorie, titre, description
  3. Details & prix : pieces (+/-), cuisine, superficie, prix, location
  4. Localisation, contact et recapitulatif

Une seule etape est affichee a la fois (ecran leger = plus fluide). L'envoi des photos
et l'enregistrement se font en arriere-plan.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import flet as ft
from services.i18n import friendly_error

FT_ICONS = ft.Icons

from components.widgets import CountryCitySelector, ImagePicker, image_kwargs, snack
from services.visitor import SessionFactory as _SessionClass
from services.config import (
    APP_CONFIG, CAT_CHAMBRE, CAT_MAISON, CAT_STUDIO, CAT_TERRAIN, CATEGORIES,
    COLORS, TRANSACTIONS, build_type_bien, get_currency,
)
from services.db import LOCAL_UPLOAD_DIR, SUPABASE_BUCKET, db
from services.i18n import t
from services.monetization import monetization

PG_INT_MAX = 2_147_483_647
CUISINE_KINDS = (CAT_MAISON, CAT_STUDIO, CAT_CHAMBRE)
RENT = "LOCATION"

SOFT = "#F3F6F4"        # fond des champs
TINT = "#E6F2EB"        # vert tres clair
TRACK = "#D9E2DC"       # barre de progression vide
CLEAR = "#00000000"

STEPS = [
    ("Photos", "Ajoutez vos photos", "Une belle annonce commence par de belles photos."),
    ("Le bien", "Parlez-nous du bien", "Type d'annonce, titre et description."),
    ("Détails & prix", "Détails et prix", "Les caractéristiques et le tarif."),
    ("Localisation", "Où et comment vous joindre ?", "Localisation, contact, puis vérifiez le récapitulatif."),
]


# ----------------------------------------------------------------- utilitaires
def _digits(value) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _opt_int(value):
    d = _digits(value)
    return int(d) if d else None


def _to_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value) -> str:
    d = _digits(str(value) if value is not None else "")
    return f"{int(d):,}".replace(",", " ") if d else ""


def _ic(name: str, fallback):
    return getattr(FT_ICONS, name, fallback)


def _page_width(page: ft.Page) -> float:
    w = getattr(page, "window_width", None) or getattr(page, "width", None)
    if not w:
        win = getattr(page, "window", None)
        w = getattr(win, "width", None) if win else None
    return w or 400


KIND_ICONS = {
    CAT_MAISON: _ic("HOME_OUTLINED", FT_ICONS.HOME),
    CAT_STUDIO: _ic("WEEKEND_OUTLINED", FT_ICONS.HOME),
    CAT_CHAMBRE: _ic("BED_OUTLINED", FT_ICONS.HOME),
    CAT_TERRAIN: _ic("LANDSCAPE_OUTLINED", FT_ICONS.HOME),
}
TX_ICONS = {
    "VENTE": _ic("SELL_OUTLINED", FT_ICONS.HOME),
    "LOCATION": _ic("KEY_OUTLINED", FT_ICONS.HOME),
}
CUISINE_OPTIONS = [("none", "Aucune"), ("interne", "Interne"), ("externe", "Externe"), ("both", "Les deux")]


def _field(label: str, **kwargs) -> ft.TextField:
    base = dict(
        label=label, border_radius=14, filled=True, bgcolor=SOFT, border_color=CLEAR,
        focused_border_color=COLORS["primary"], focused_bgcolor="#FFFFFF",
        content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
    )
    base.update(kwargs)
    return ft.TextField(**base)


def _num_field(label: str, **kwargs) -> ft.TextField:
    if hasattr(ft, "NumbersOnlyInputFilter"):
        kwargs.setdefault("input_filter", ft.NumbersOnlyInputFilter())
    kwargs.setdefault("keyboard_type", ft.KeyboardType.NUMBER)
    return _field(label, **kwargs)


def _dropdown(label: str, options, value) -> ft.Dropdown:
    return ft.Dropdown(label=label, options=options, value=value, expand=True, border_radius=14,
                       filled=True, bgcolor=SOFT, border_color=CLEAR, focused_border_color=COLORS["primary"])


def _delete_photo_file(url: str) -> None:
    """Supprime le fichier d'une photo retiree (Cloudinary, Supabase ou local)."""
    try:
        if not url:
            return
        if "cloudinary.com" in url:
            db.delete_photo_cloudinary(url)
            return
        if url.startswith("http"):
            name = Path(urlparse(url).path).name
            if db.mode == "supabase" and db.client:
                try:
                    db.client.storage.from_(SUPABASE_BUCKET).remove([name])
                except Exception:
                    pass
            candidates = [LOCAL_UPLOAD_DIR / name]
        else:
            clean = url.strip().lstrip("/")
            candidates = [Path(clean), Path("assets") / clean, LOCAL_UPLOAD_DIR / Path(clean).name]
        for c in candidates:
            if c.is_file():
                c.unlink()
                break
    except Exception as ex:
        print(f"[Photo] suppression impossible {url}: {ex}")


def _appbar(page: ft.Page, title: str, back_route: str) -> ft.AppBar:
    return ft.AppBar(
        leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go(back_route)),
        title=ft.Text(title, color="#FFFFFF", weight=ft.FontWeight.BOLD),
        bgcolor=COLORS["primary"], elevation=0,
    )


def _locked_view(page: ft.Page, msg: str) -> ft.View:
    go_premium = lambda e: page.go("/premium")
    return ft.View(
        route="/publish", bgcolor=COLORS["bg"], appbar=_appbar(page, t("publish_title"), "/home"),
        controls=[ft.Container(
            alignment=ft.alignment.center, expand=True, padding=20,
            content=ft.Container(
                width=520, bgcolor="#FFFFFF", border_radius=22, padding=22,
                content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12, controls=[
                    ft.Icon(FT_ICONS.LOCK_OUTLINED, size=64, color=COLORS["muted"]),
                    ft.Text("Limite atteinte", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(msg, text_align=ft.TextAlign.CENTER, color=COLORS["muted"]),
                    ft.Container(height=10),
                    ft.ElevatedButton("Passer en PRO - 5000 FCFA/mois", icon=FT_ICONS.STAR, on_click=go_premium,
                                      style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF"),
                                      expand=True, height=48),
                    ft.OutlinedButton("Acheter un Boost - 1000 FCFA", icon=FT_ICONS.ROCKET_LAUNCH,
                                      on_click=go_premium, expand=True),
                    ft.TextButton("Voir mes annonces", on_click=lambda e: page.go("/mes-annonces")),
                ])))],
    )


# ------------------------------------------------------------------------ vue
def publish_view(page: ft.Page, bien_id: str = None) -> ft.View:
    Session = _SessionClass.bind(page)
    if not Session.user:
        page.go("/login")
        return ft.View(route="/publish")

    is_edit = bien_id is not None
    existing = None
    if is_edit:
        existing = db.get_bien(bien_id)
        if not existing:
            snack(page, "Annonce introuvable", error=True)
            page.go("/mes-annonces")
            return ft.View(route="/mes-annonces")
        if existing.get("user_id") != Session.user["id"] and not Session.is_admin():
            snack(page, "Non autorisé", error=True)
            page.go("/mes-annonces")
            return ft.View(route="/mes-annonces")
    else:
        try:
            total = len(db.list_biens(user_id=Session.user["id"]))
        except Exception:
            total = 0
        can_pub, msg = monetization.can_publish(Session.user, total)
        if not can_pub:
            return _locked_view(page, msg)

    user = Session.user
    ex = existing or {}
    max_photos = APP_CONFIG["MAX_PHOTOS"]
    photos: List[str] = list(ex.get("photos") or [])
    original_photos = set(photos)

    width = _page_width(page)
    is_desktop = width >= 900
    box_w = min(width, 680)
    CONTENT_W = int(box_w - 32)          # largeur utile (marges de page)
    INNER_W = CONTENT_W - 32             # a l'interieur d'une carte
    THUMB = max(76, min(120, int((INNER_W - 20) / 3)))
    TILE_W = int((CONTENT_W - 12) / 2)
    COVER_H = 280 if is_desktop else 200

    def g(field, default=""):
        return str(ex.get(field) or default) if is_edit else default

    def _cuisine_init():
        if not is_edit:
            return "interne"
        if ex.get("cuisines") == 0:
            return "none"
        i, e_ = bool(ex.get("cuisine_interne")), bool(ex.get("cuisine_externe"))
        if i and e_:
            return "both"
        return "externe" if e_ else "interne"

    sel = {
        "tx": ex.get("transaction") if ex.get("transaction") in TRANSACTIONS else TRANSACTIONS[0],
        "kind": ex.get("categorie") if ex.get("categorie") in CATEGORIES else CAT_MAISON,
        "cuisine": _cuisine_init(),
        "step": 1,
    }
    vals = {
        "rooms": max(1, _to_int(ex.get("chambres"), 1)) if is_edit else 1,
        "showers": _to_int(ex.get("salles_de_bain"), 1) if is_edit else 1,
        "living": _to_int(ex.get("salons"), 1) if is_edit else 1,
    }
    busy = {"v": False}

    # ------------------------------------------------------------ composants
    def card(controls, padding=16):
        return ft.Container(
            bgcolor="#FFFFFF", border_radius=22, padding=padding,
            shadow=ft.BoxShadow(blur_radius=18, color="#0D000000", offset=ft.Offset(0, 4)),
            content=ft.Column(spacing=14, controls=controls))

    def head(title, subtitle):
        return ft.Column(spacing=2, controls=[
            ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Text(subtitle, size=13, color=COLORS["muted"])])

    def caption(text):
        return ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=COLORS["muted"])

    def pill(label, selected, on_click):
        return ft.Container(
            ink=True, on_click=on_click, border_radius=20,
            padding=ft.padding.symmetric(horizontal=16, vertical=9),
            bgcolor=COLORS["primary"] if selected else SOFT,
            content=ft.Text(label, size=13, weight=ft.FontWeight.W_600,
                            color="#FFFFFF" if selected else COLORS["text"]))

    def switch_row(icon, label, switch):
        return ft.Container(
            bgcolor=SOFT, border_radius=14, padding=ft.padding.only(left=14, right=6, top=2, bottom=2),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Icon(icon, size=20, color=COLORS["primary"]),
                ft.Text(label, size=14, expand=True), switch]))

    # ---------------------------------------------------------------- champs
    title = _field(t("title_label"), value=g("titre"))
    description = _field(t("description_label"), multiline=True, min_lines=4, max_lines=8, value=g("description"))

    surface = _num_field(t("surface_label"), value=g("superficie"))
    price = _num_field(
        t("price_label"), value=g("prix"),
        text_style=ft.TextStyle(size=22, weight=ft.FontWeight.BOLD),
        suffix_text=get_currency(ex.get("country_code") if is_edit else user.get("country_code")))
    negotiable = ft.Switch(value=bool(ex.get("prix_discutable")) if is_edit else False,
                           active_color=COLORS["primary"])
    on_site = ft.Switch(value=bool(ex.get("prix_sur_place")) if is_edit else False,
                        active_color=COLORS["primary"])
    price.disabled = bool(on_site.value)

    def _avance_default():
        return str(_to_int(ex.get("avance_mois") or ex.get("avance") or 0)) if is_edit else "3"

    def _caution_default():
        return str(_to_int(ex.get("caution_mois") or ex.get("caution") or 0)) if is_edit else "1"

    avance_dd = _dropdown("Avance loyer", [ft.dropdown.Option("0", "Pas d'avance")] +
                          [ft.dropdown.Option(str(n), f"{n} mois") for n in (1, 2, 3, 6, 8, 10, 12)],
                          _avance_default())
    caution_dd = _dropdown("Caution", [ft.dropdown.Option("0", "Pas de caution")] +
                           [ft.dropdown.Option(str(n), f"{n} mois") for n in (1, 2, 3)],
                           _caution_default())
    rent_block = ft.Container(
        bgcolor=TINT, border_radius=16, padding=14,
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=8, controls=[
                ft.Icon(_ic("RECEIPT_LONG_OUTLINED", FT_ICONS.HOME), size=18, color=COLORS["primary"]),
                ft.Text("Conditions de location", size=13, weight=ft.FontWeight.BOLD, color=COLORS["primary"])]),
            ft.Row([avance_dd, caution_dd], spacing=8)]))

    def on_country(code: str):
        price.suffix_text = get_currency(code)
        refresh_price_hint()

    geo = CountryCitySelector(page, ex.get("country_code") if is_edit else user.get("country_code"),
                              ex.get("city") if is_edit else user.get("city"), on_country=on_country)
    for _name in ("country_dd", "city_dd", "city_other"):
        _c = getattr(geo, _name, None)
        if _c is not None:
            try:
                _c.bgcolor, _c.border_color, _c.border_radius = SOFT, CLEAR, 14
            except Exception:
                pass
    locality = _field(t("zone_label"), prefix_icon=FT_ICONS.LOCATION_ON,
                      value=(ex.get("locality") or "") if is_edit else (user.get("locality") or ""))
    whatsapp = _field(t("whatsapp_number_label"), keyboard_type=ft.KeyboardType.PHONE, prefix_icon=FT_ICONS.PHONE,
                      value=(ex.get("whatsapp") or "") if is_edit else (user.get("phone") or ""))
    whatsapp2 = _field("2ème numéro (optionnel)", keyboard_type=ft.KeyboardType.PHONE, prefix_icon=FT_ICONS.PHONE,
                       value=(ex.get("whatsapp2") or ex.get("whatsapp_2") or "") if is_edit else "")

    # ------------------------------------------------------------- erreurs
    def fail(msg, field=None):
        if field is not None:
            field.error_text = "Obligatoire"
            try:
                field.update()
            except Exception:
                pass
        snack(page, msg, error=True)
        return False

    def clear_error(e):
        if e.control.error_text:
            e.control.error_text = None
            e.control.update()

    for _f in (title, locality, whatsapp, surface):
        _f.on_change = clear_error

    def refresh_price_hint():
        d = _digits(price.value)
        rent = sel["tx"] == RENT
        if on_site.value or not d:
            price.helper_text = None
        else:
            price.helper_text = f"{_fmt(d)} {get_currency(geo.country_code)}" + (" / mois" if rent else "")

    def on_price_change(e):
        if price.error_text:
            price.error_text = None
        refresh_price_hint()
        price.update()

    price.on_change = on_price_change
    refresh_price_hint()

    def on_site_change(e):
        price.disabled = bool(on_site.value)
        if on_site.value:
            price.error_text = None
        refresh_price_hint()
        price.update()

    on_site.on_change = on_site_change

    # ---------------------------------------------------------- etape 2 : choix
    tx_box = ft.Container()
    kind_box = ft.Row(spacing=12, run_spacing=12, wrap=True)

    def tx_segmented():
        def opt(tr):
            on = sel["tx"] == tr
            return ft.Container(
                expand=True, ink=True, on_click=lambda e, v=tr: pick_tx(v), border_radius=14,
                padding=ft.padding.symmetric(vertical=12),
                bgcolor="#FFFFFF" if on else CLEAR,
                shadow=ft.BoxShadow(blur_radius=8, color="#14000000", offset=ft.Offset(0, 2)) if on else None,
                content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=8, controls=[
                    ft.Icon(TX_ICONS.get(tr, FT_ICONS.HOME), size=20,
                            color=COLORS["primary"] if on else COLORS["muted"]),
                    ft.Text(t(f"tx_filter_{tr}"), size=14, weight=ft.FontWeight.BOLD,
                            color=COLORS["primary"] if on else COLORS["muted"])]))
        return ft.Container(bgcolor="#E1E9E4", border_radius=18, padding=4,
                            content=ft.Row(spacing=4, controls=[opt(tr) for tr in TRANSACTIONS]))

    def kind_tile(c):
        on = sel["kind"] == c
        return ft.Container(
            width=TILE_W, ink=True, on_click=lambda e, v=c: pick_kind(v), border_radius=20, padding=14,
            bgcolor=TINT if on else "#FFFFFF",
            border=ft.border.all(2, COLORS["primary"] if on else "#FFFFFF"),
            shadow=ft.BoxShadow(blur_radius=14, color="#0D000000", offset=ft.Offset(0, 3)),
            content=ft.Column(spacing=12, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Container(width=42, height=42, border_radius=13, alignment=ft.alignment.center,
                                 bgcolor=COLORS["primary"] if on else SOFT,
                                 content=ft.Icon(KIND_ICONS[c], size=22,
                                                 color="#FFFFFF" if on else COLORS["primary"])),
                    ft.Icon(FT_ICONS.CHECK_CIRCLE, size=22, color=COLORS["primary"])
                    if on else ft.Container(width=22, height=22)]),
                ft.Text(t(f"category_{c}"), size=15, weight=ft.FontWeight.BOLD, color=COLORS["text"])]))

    def build_choices():
        tx_box.content = tx_segmented()
        kind_box.controls = [kind_tile(c) for c in CATEGORIES]

    def pick_tx(v):
        sel["tx"] = v
        build_choices()
        apply_rules()
        page.update()

    def pick_kind(v):
        sel["kind"] = v
        build_choices()
        apply_rules()
        page.update()

    # -------------------------------------------------------- etape 3 : details
    def stepper(icon, label, key, minimum, maximum=30):
        num = ft.Text(str(vals[key]), size=20, weight=ft.FontWeight.BOLD, width=36,
                      text_align=ft.TextAlign.CENTER)

        def bump(d):
            vals[key] = max(minimum, min(maximum, vals[key] + d))
            num.value = str(vals[key])
            num.update()

        def round_btn(ic, d):
            return ft.IconButton(ic, icon_size=20, icon_color=COLORS["primary"], bgcolor=TINT,
                                 on_click=lambda e: bump(d))

        return ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Container(width=40, height=40, border_radius=12, bgcolor=SOFT, alignment=ft.alignment.center,
                         content=ft.Icon(icon, size=22, color=COLORS["primary"])),
            ft.Text(label, size=15, weight=ft.FontWeight.W_500, expand=True),
            round_btn(FT_ICONS.REMOVE, -1), num, round_btn(FT_ICONS.ADD, 1)])

    rooms_card = card([
        caption("PIÈCES"),
        stepper(_ic("BED_OUTLINED", FT_ICONS.HOME), t("rooms_label"), "rooms", 1),
        stepper(_ic("BATHTUB_OUTLINED", FT_ICONS.HOME), t("showers_label"), "showers", 0),
        stepper(_ic("WEEKEND_OUTLINED", FT_ICONS.HOME), t("living_rooms_label"), "living", 0),
    ])

    cuisine_row = ft.Row(spacing=8, run_spacing=8, wrap=True)

    def build_cuisine():
        cuisine_row.controls = [pill(lbl, sel["cuisine"] == key, lambda e, k=key: pick_cuisine(k))
                                for key, lbl in CUISINE_OPTIONS]

    def pick_cuisine(k):
        sel["cuisine"] = k
        build_cuisine()
        cuisine_row.update()

    build_cuisine()
    cuisine_card = card([caption("CUISINE"), cuisine_row])
    surface_card = card([caption("SUPERFICIE"), surface])
    price_card = card([
        caption("PRIX"), price,
        switch_row(_ic("HANDSHAKE_OUTLINED", FT_ICONS.PAYMENTS_OUTLINED), t("negotiable_checkbox"), negotiable),
        switch_row(_ic("PLACE_OUTLINED", FT_ICONS.LOCATION_ON_OUTLINED), t("price_on_site_checkbox"), on_site),
        rent_block,
    ])

    def apply_rules():
        kind = sel["kind"]
        rent = sel["tx"] == RENT
        rooms_card.visible = kind == CAT_MAISON
        cuisine_card.visible = kind in CUISINE_KINDS
        surface.label = t("surface_label") + (" *" if kind == CAT_TERRAIN else "")
        rent_block.visible = rent
        refresh_price_hint()

    # ----------------------------------------------------------- etape 1 : photos
    upload_status = ft.Row(visible=False, spacing=8, controls=[
        ft.ProgressRing(width=16, height=16, stroke_width=2, color=COLORS["primary"]),
        ft.Text("Envoi des photos...", size=12, color=COLORS["muted"])])
    photos_box = ft.Container()
    photos_count = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=COLORS["primary"])

    def set_uploading(flag: bool):
        upload_status.visible = flag
        page.update()

    def remove_photo(u):
        if u in photos:
            photos.remove(u)
        if u not in original_photos:  # envoyee pendant cette session : on supprime le fichier tout de suite
            threading.Thread(target=_delete_photo_file, args=(u,), daemon=True).start()
        render_photos()

    def make_cover(i):
        if 0 < i < len(photos):
            photos.insert(0, photos.pop(i))
            render_photos()

    def close_btn(u):
        return ft.Container(top=6, right=6, content=ft.IconButton(
            FT_ICONS.CLOSE, icon_size=15, icon_color="#FFFFFF", bgcolor="#8C000000",
            on_click=lambda e, x=u: remove_photo(x)))

    def cover_view(u):
        return ft.Stack(width=INNER_W, height=COVER_H, controls=[
            ft.Container(width=INNER_W, height=COVER_H, border_radius=18, bgcolor="#EEF2EF",
                         clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                         content=ft.Image(**image_kwargs(u, width=900), width=INNER_W, height=COVER_H,
                                          fit=ft.ImageFit.COVER, error_content=ft.Container(bgcolor="#DDE4DF"))),
            close_btn(u),
            ft.Container(left=10, bottom=10, bgcolor=COLORS["primary"], border_radius=12,
                         padding=ft.padding.symmetric(horizontal=10, vertical=4),
                         content=ft.Text("Couverture", size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"))])

    def thumb_view(u, i):
        return ft.Stack(width=THUMB, height=THUMB, controls=[
            ft.Container(width=THUMB, height=THUMB, border_radius=14, bgcolor="#EEF2EF", ink=True,
                         clip_behavior=ft.ClipBehavior.ANTI_ALIAS, on_click=lambda e, k=i: make_cover(k),
                         content=ft.Image(**image_kwargs(u, width=240), width=THUMB, height=THUMB,
                                          fit=ft.ImageFit.COVER, error_content=ft.Container(bgcolor="#DDE4DF"))),
            close_btn(u)])

    def on_files(paths: List[str]):
        set_uploading(True)
        try:
            for path in paths:
                if len(photos) >= max_photos:
                    snack(page, t("max_photos", n=max_photos), error=True)
                    break
                try:
                    photos.append(db.upload_photo(path))
                    render_photos()
                except Exception as exc:
                    snack(page, friendly_error(exc), error=True)
        finally:
            set_uploading(False)

    picker = ImagePicker(page, "publish", on_files, multiple=True,
                         limit=lambda: max_photos - len(photos),
                         on_overflow=lambda: snack(page, t("max_photos", n=max_photos), error=True))

    big_add = ft.Container(
        width=INNER_W, height=190, border_radius=18, ink=True, on_click=picker.open,
        gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
                                   colors=[TINT, "#F6FAF7"]),
        border=ft.border.all(1.5, "#BFD9C9"), alignment=ft.alignment.center,
        content=ft.Column(tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER, spacing=6, controls=[
            ft.Container(width=64, height=64, border_radius=32, bgcolor=COLORS["primary"],
                         alignment=ft.alignment.center,
                         content=ft.Icon(FT_ICONS.ADD_A_PHOTO_OUTLINED, size=30, color="#FFFFFF")),
            ft.Text("Ajouter des photos", size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Text(f"Jusqu'à {max_photos} photos depuis votre galerie", size=12, color=COLORS["muted"])]))
    small_add = ft.Container(
        width=THUMB, height=THUMB, border_radius=14, bgcolor=TINT, ink=True, on_click=picker.open,
        border=ft.border.all(1.5, "#BFD9C9"), alignment=ft.alignment.center,
        content=ft.Column(tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                          alignment=ft.MainAxisAlignment.CENTER, spacing=2, controls=[
            ft.Icon(FT_ICONS.ADD, size=28, color=COLORS["primary"]),
            ft.Text("Ajouter", size=11, color=COLORS["primary"])]))

    def render_photos(update: bool = True):
        photos_count.value = f"{len(photos)}/{max_photos}"
        if not photos:
            photos_box.content = big_add
        else:
            rest = [thumb_view(u, i) for i, u in enumerate(photos) if i > 0]
            if len(photos) < max_photos:
                rest.append(small_add)
            col = [cover_view(photos[0]), ft.Row(controls=rest, wrap=True, spacing=10, run_spacing=10)]
            if len(photos) > 1:
                col.append(ft.Text("Touchez une photo pour en faire la couverture", size=11,
                                   color=COLORS["muted"]))
            photos_box.content = ft.Column(spacing=12, controls=col)
        if update:
            page.update()

    # ------------------------------------------------------ etape 4 : recapitulatif
    recap_box = ft.Container()

    def build_recap():
        d = _digits(price.value)
        rent = sel["tx"] == RENT
        if on_site.value:
            price_txt = t("price_on_site")
        elif d:
            price_txt = f"{_fmt(d)} {get_currency(geo.country_code)}" + (" / mois" if rent else "")
        else:
            price_txt = "-"
        thumb = (ft.Container(width=76, height=76, border_radius=16, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                              content=ft.Image(**image_kwargs(photos[0], width=240), width=76, height=76,
                                               fit=ft.ImageFit.COVER)) if photos else ft.Container(width=0))
        recap_box.content = card([
            caption("RÉCAPITULATIF"),
            ft.Row(spacing=14, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                thumb,
                ft.Column(spacing=3, expand=True, controls=[
                    ft.Text((title.value or "").strip() or "Sans titre", size=15, weight=ft.FontWeight.BOLD,
                            max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"{t('tx_filter_' + sel['tx'])} · {t('category_' + sel['kind'])}", size=12,
                            color=COLORS["muted"]),
                    ft.Text(price_txt, size=16, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                    ft.Text(f"{geo.city} - {(locality.value or '').strip()}", size=12, color=COLORS["muted"])])]),
            ft.Row(spacing=6, controls=[
                ft.Icon(FT_ICONS.PHOTO_LIBRARY_OUTLINED if hasattr(FT_ICONS, "PHOTO_LIBRARY_OUTLINED")
                        else FT_ICONS.ADD_A_PHOTO_OUTLINED, size=16, color=COLORS["muted"]),
                ft.Text(f"{len(photos)} photo(s)", size=12, color=COLORS["muted"])]),
        ])

    # ------------------------------------------------------------- validation
    def validate(step: int) -> bool:
        if step == 1:
            if not photos:
                return fail(t("photo_required"))
        elif step == 2:
            if not (title.value or "").strip():
                return fail(t("title_required"), title)
        elif step == 3:
            if sel["kind"] == CAT_TERRAIN and (not _digits(surface.value) or int(_digits(surface.value)) <= 0):
                return fail(t("surface_required"), surface)
            if not on_site.value:
                if not _digits(price.value):
                    return fail(t("price_required"), price)
                if int(_digits(price.value)) > PG_INT_MAX:
                    return fail(t("invalid_price"), price)
        elif step == 4:
            if not geo.city:
                return fail(t("country_city_required"))
            if not (locality.value or "").strip():
                return fail(t("zone_required_publish"), locality)
            if not (whatsapp.value or "").strip():
                return fail(t("whatsapp_required"), whatsapp)
        return True

    # ------------------------------------------------------------- publication
    def set_busy(flag: bool):
        busy["v"] = flag
        next_btn.disabled = flag
        next_btn.text = "Enregistrement..." if flag else last_label
        page.update()

    last_label = "Enregistrer les modifications" if is_edit else t("publish_button")

    def do_publish():
        if busy["v"]:
            return
        for s in (1, 2, 3, 4):
            if not validate(s):
                if sel["step"] != s:
                    show_step(s)
                return
        kind, tx = sel["kind"], sel["tx"]
        extra = {}
        if kind == CAT_MAISON:
            extra.update(chambres=vals["rooms"], salles_de_bain=vals["showers"], salons=vals["living"])
        if kind in CUISINE_KINDS:
            c = sel["cuisine"]
            if c == "none":
                extra.update(cuisines=0, nb_cuisines=0, cuisine_type="")
            else:
                interne, externe = c in ("interne", "both"), c in ("externe", "both")
                extra.update(cuisine_interne=interne, cuisine_externe=externe, cuisines=1, nb_cuisines=1,
                             cuisine_type="Int + Ext" if (interne and externe) else ("Interne" if interne else "Externe"))
        surface_val = _opt_int(surface.value)
        if surface_val is not None:
            extra["superficie"] = surface_val

        prix = None if on_site.value else int(_digits(price.value))
        rent = tx == RENT
        avance_val = _to_int(avance_dd.value) if rent else 0
        caution_val = _to_int(caution_dd.value) if rent else 0

        payload = {
            "titre": title.value.strip(), "type_bien": build_type_bien(tx, kind),
            "transaction": tx, "categorie": kind, "country_code": geo.country_code, "city": geo.city,
            "locality": locality.value.strip(), "prix": prix, "prix_discutable": bool(negotiable.value),
            "prix_sur_place": bool(on_site.value), "whatsapp": whatsapp.value.strip(),
            "whatsapp2": (whatsapp2.value or "").strip() or None,
            "description": (description.value or "").strip(), "photos": list(photos),
            "avance_mois": avance_val, "caution_mois": caution_val,
            "avance": avance_val, "caution": caution_val,
            **extra,
        }
        set_busy(True)

        def work():
            try:
                if is_edit:
                    db.update_bien(bien_id, payload)
                    for url in original_photos - set(payload["photos"]):
                        _delete_photo_file(url)
                    snack(page, "Annonce modifiée avec succès")
                else:
                    payload["user_id"] = user["id"]
                    db.create_bien(payload)
                    snack(page, t("publish_success"))
                page.go("/mes-annonces" if is_edit else "/home")
            except Exception as exc:
                print(f"[PUBLISH] {exc}")
                set_busy(False)
                snack(page, friendly_error(exc), error=True)

        threading.Thread(target=work, daemon=True).start()

    # -------------------------------------------------------------- navigation
    seg_row = ft.Row(spacing=6)
    step_label = ft.Text("", size=12, color=COLORS["muted"], weight=ft.FontWeight.W_600)

    next_btn = ft.ElevatedButton(
        "Continuer", icon=FT_ICONS.ARROW_FORWARD, expand=True, height=52,
        on_click=lambda e: go_next(),
        style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF",
                             shape=ft.RoundedRectangleBorder(radius=16)))
    back_btn = ft.OutlinedButton(
        "Retour", icon=FT_ICONS.ARROW_BACK, height=52, visible=False,
        on_click=lambda e: go_prev(),
        style=ft.ButtonStyle(color=COLORS["primary"], shape=ft.RoundedRectangleBorder(radius=16),
                             side=ft.BorderSide(1.2, COLORS["primary"])))

    panels = {
        1: ft.Column(spacing=16, controls=[
            head(*STEPS[0][1:]),
            card([ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                      ft.Text("Galerie", size=13, weight=ft.FontWeight.W_600), photos_count]),
                  upload_status, photos_box])]),
        2: ft.Column(spacing=16, controls=[
            head(*STEPS[1][1:]), tx_box, caption("TYPE DE BIEN"), kind_box,
            card([title, description])]),
        3: ft.Column(spacing=16, controls=[
            head(*STEPS[2][1:]), rooms_card, cuisine_card, surface_card, price_card]),
        4: ft.Column(spacing=16, controls=[
            head(*STEPS[3][1:]),
            card([caption("LOCALISATION"), *geo.controls, locality]),
            card([caption("CONTACT"), whatsapp, whatsapp2]),
            recap_box]),
    }

    try:
        step_host = ft.AnimatedSwitcher(content=panels[1], transition=ft.AnimatedSwitcherTransition.FADE,
                                        duration=220, reverse_duration=0)
    except Exception:
        step_host = ft.Container(content=panels[1])

    scroll_col = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0, controls=[
        ft.Container(padding=ft.padding.only(left=16, right=16, top=8, bottom=24), content=step_host)])

    def refresh_chrome():
        n = sel["step"]
        seg_row.controls = [
            ft.Container(expand=True, height=6, border_radius=3,
                         bgcolor=COLORS["primary"] if i < n else TRACK,
                         on_click=lambda e, k=i + 1: goto(k)) for i in range(len(STEPS))]
        step_label.value = f"Étape {n} sur {len(STEPS)} · {STEPS[n - 1][0]}"
        back_btn.visible = n > 1
        last = n == len(STEPS)
        next_btn.text = last_label if last else "Continuer"
        next_btn.icon = FT_ICONS.CHECK if last else FT_ICONS.ARROW_FORWARD

    def show_step(n: int):
        sel["step"] = n
        if n == 4:
            build_recap()
        step_host.content = panels[n]
        refresh_chrome()
        try:
            scroll_col.scroll_to(offset=0, duration=200)
        except Exception:
            pass
        page.update()

    def goto(n: int):
        if n < sel["step"] or is_edit:   # en creation on ne saute pas en avant
            show_step(n)

    def go_next():
        if busy["v"]:
            return
        n = sel["step"]
        if not validate(n):
            return
        if n < len(STEPS):
            show_step(n + 1)
        else:
            do_publish()

    def go_prev():
        if sel["step"] > 1:
            show_step(sel["step"] - 1)

    # --------------------------------------------------------------- assemblage
    build_choices()
    apply_rules()
    render_photos(update=False)
    refresh_chrome()

    progress = ft.Container(
        bgcolor=COLORS["bg"], padding=ft.padding.only(left=16, right=16, top=12, bottom=4),
        content=ft.Column(spacing=8, controls=[seg_row, step_label]))
    bottom_bar = ft.Container(
        bgcolor="#FFFFFF", padding=ft.padding.symmetric(horizontal=16, vertical=12),
        shadow=ft.BoxShadow(blur_radius=16, color="#14000000", offset=ft.Offset(0, -4)),
        content=ft.Row(spacing=10, controls=[back_btn, next_btn]))

    w = 680 if is_desktop else None
    root = ft.Column(
        expand=True, spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER if is_desktop else ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.Container(width=w, content=progress),
            ft.Container(width=w, expand=True, content=scroll_col),
            ft.Container(width=w, content=bottom_bar),
        ])

    return ft.View(
        route=f"/edit/{bien_id}" if is_edit else "/publish",
        bgcolor=COLORS["bg"], padding=0,
        appbar=_appbar(page, "Modifier l'annonce" if is_edit else t("publish_title"),
                       "/mes-annonces" if is_edit else "/home"),
        controls=[root],
    )
