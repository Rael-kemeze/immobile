"""Publication d'une annonce."""

from __future__ import annotations
from typing import List, Optional
import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons


from components.widgets import CountryCitySelector, ImagePicker, image_kwargs, primary_button, snack, text_field, responsive_wrapper
from services.auth import Session
from services.config import APP_CONFIG, CAT_CHAMBRE, CAT_MAISON, CAT_STUDIO, CAT_TERRAIN, CATEGORIES, COLORS, TRANSACTIONS, build_type_bien, get_currency
from services.db import db, LOCAL_UPLOAD_DIR, WEB_UPLOAD_DIR
from pathlib import Path
from services.monetization import monetization
from services.i18n import t

PG_INT_MAX = 2_147_483_647

def _digits(value) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())

def _opt_int(value):
    d = _digits(value)
    return int(d) if d else None

def publish_view(page: ft.Page, bien_id: str = None) -> ft.View:
    if not Session.user:
        page.go("/login")
        return ft.View(route="/publish")

    is_edit = bien_id is not None
    existing_bien = None
    if is_edit:
        existing_bien = db.get_bien(bien_id)
        if not existing_bien:
            snack(page, "Annonce introuvable", error=True)
            page.go("/mes-annonces")
            return ft.View(route="/mes-annonces")
        # Securité: seul proprio ou admin peut modifier
        if existing_bien.get("user_id") != Session.user["id"] and not Session.is_admin():
            snack(page, "Non autorisé", error=True)
            page.go("/mes-annonces")
            return ft.View(route="/mes-annonces")

    # Monetization check seulement en création
    if not is_edit:
        try:
            my_biens = db.list_biens(user_id=Session.user["id"])
            total = len(my_biens)
        except:
            total = 0
        
        can_pub, msg = monetization.can_publish(Session.user, total)
        if not can_pub:
            def go_premium(e):
                page.go("/premium")
            return ft.View(
                route="/publish",
                bgcolor=COLORS["bg"],
                appbar=ft.AppBar(leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/home")), title=ft.Text(t("publish_title"), color="#FFFFFF", weight=ft.FontWeight.BOLD), bgcolor=COLORS["primary"]),
                controls=[
                    ft.Container(
                        alignment=ft.alignment.center,
                        expand=True,
                        padding=20,
                        content=ft.Container(
                            width=520,
                            bgcolor="#FFFFFF",
                            border_radius=16,
                            padding=20,
                            content=ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=12,
                                controls=[
                                    ft.Icon(FT_ICONS.LOCK_OUTLINED, size=64, color=COLORS["muted"]),
                                    ft.Text("Limite atteinte", size=20, weight=ft.FontWeight.BOLD),
                                    ft.Text(msg, text_align=ft.TextAlign.CENTER, color=COLORS["muted"]),
                                    ft.Container(height=10),
                                    ft.ElevatedButton("Passer en PRO - 5000 FCFA/mois", icon=FT_ICONS.STAR, on_click=go_premium, style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF"), expand=True, height=48),
                                    ft.OutlinedButton("Acheter un Boost - 1000 FCFA", icon=FT_ICONS.ROCKET_LAUNCH, on_click=go_premium, expand=True),
                                    ft.TextButton("Voir mes annonces", on_click=lambda e: page.go("/mes-annonces")),
                                ]
                            )
                        )
                    )
                ]
            )

    user = Session.user
    max_photos = APP_CONFIG["MAX_PHOTOS"]
    photos: List[str] = list(existing_bien.get("photos", []) if is_edit and existing_bien else [])

    is_desktop = (page.window_width or 0) >= 900

    def dropdown(label, options, value):
        return ft.Dropdown(label=label, border_radius=12, filled=True, bgcolor="#FFFFFF", options=options, value=value)

    # Pré-remplissage si edit
    def _get(field, default=""):
        if is_edit and existing_bien:
            return str(existing_bien.get(field) or default)
        return default

    title = text_field(t("title_label"), value=_get("titre"))
    # transaction et categorie
    init_tx = existing_bien.get("transaction") if is_edit else TRANSACTIONS[0]
    init_cat = existing_bien.get("categorie") if is_edit else CAT_MAISON
    transaction_dd = dropdown(t("transaction_label"), [ft.dropdown.Option(tr, t(f"transaction_{tr}")) for tr in TRANSACTIONS], init_tx)
    kind_dd = dropdown(t("kind_label"), [ft.dropdown.Option(c, t(f"category_{c}")) for c in CATEGORIES], init_cat)

    rooms = text_field(t("rooms_label"), keyboard_type=ft.KeyboardType.NUMBER, value=_get("chambres"))
    showers = text_field(t("showers_label"), keyboard_type=ft.KeyboardType.NUMBER, value=_get("salles_de_bain"))
    living = text_field(t("living_rooms_label"), keyboard_type=ft.KeyboardType.NUMBER, value=_get("salons"))
    house_row = ft.Row([ft.Container(rooms, expand=True), ft.Container(showers, expand=True), ft.Container(living, expand=True)], spacing=8)

    has_cuisine = ft.Checkbox(label="A une cuisine ?", value=existing_bien.get("cuisines", 1) != 0 if is_edit else True)
    cuisine_interne = ft.Checkbox(label="Cuisine interne", value=existing_bien.get("cuisine_interne", True) if is_edit else True)
    cuisine_externe = ft.Checkbox(label="Cuisine externe", value=existing_bien.get("cuisine_externe", False) if is_edit else False)
    cuisine_row = ft.Row([cuisine_interne, cuisine_externe], spacing=12)
    cuisine_bloc = ft.Column(spacing=6, controls=[has_cuisine, ft.Container(content=cuisine_row, padding=ft.padding.only(left=12))])

    def on_cuisine_change(e):
        cuisine_row.visible = bool(has_cuisine.value)
        page.update()
    has_cuisine.on_change = on_cuisine_change
    cuisine_row.visible = bool(has_cuisine.value)

    surface = text_field(t("surface_label"), keyboard_type=ft.KeyboardType.NUMBER, value=_get("superficie"))

    def apply_kind():
        kind = kind_dd.value
        house_row.visible = kind == CAT_MAISON
        cuisine_bloc.visible = kind in [CAT_MAISON, CAT_STUDIO, CAT_CHAMBRE]
        surface.label = t("surface_label") + (" *" if kind == CAT_TERRAIN else "")
    apply_kind()
    def on_kind_change(e):
        apply_kind(); page.update()
    kind_dd.on_change = on_kind_change

    price = text_field(t("price_label"), keyboard_type=ft.KeyboardType.NUMBER, suffix_text=get_currency(user.get("country_code")), value=_get("prix"))
    negotiable = ft.Checkbox(label=t("negotiable_checkbox"), value=existing_bien.get("prix_discutable", False) if is_edit else False)
    on_site = ft.Checkbox(label=t("price_on_site_checkbox"), value=existing_bien.get("prix_sur_place", False) if is_edit else False)
    
    # === NOUVEAU: Avance et Caution (spécifique location Cameroun) ===
    def _get_avance():
        if is_edit and existing_bien:
            v = existing_bien.get("avance_mois") or existing_bien.get("avance") or 0
            try:
                return str(int(v))
            except:
                return "0"
        return "3"
    
    def _get_caution():
        if is_edit and existing_bien:
            v = existing_bien.get("caution_mois") or existing_bien.get("caution") or 0
            try:
                return str(int(v))
            except:
                return "0"
        return "1"
    
    AVANCE_OPTIONS = [
        ft.dropdown.Option("0", "Pas d'avance"),
        ft.dropdown.Option("1", "1 mois"),
        ft.dropdown.Option("2", "2 mois"),
        ft.dropdown.Option("3", "3 mois"),
        ft.dropdown.Option("6", "6 mois"),
        ft.dropdown.Option("8", "8 mois"),
        ft.dropdown.Option("10", "10 mois"),
        ft.dropdown.Option("12", "12 mois"),
    ]
    CAUTION_OPTIONS = [
        ft.dropdown.Option("0", "Pas de caution"),
        ft.dropdown.Option("1", "1 mois"),
        ft.dropdown.Option("2", "2 mois"),
        ft.dropdown.Option("3", "3 mois"),
    ]
    
    avance_dd = ft.Dropdown(
        label="Avance loyer",
        border_radius=12, filled=True, bgcolor="#FFFFFF",
        options=AVANCE_OPTIONS,
        value=_get_avance(),
        dense=True,
    )
    caution_dd = ft.Dropdown(
        label="Caution",
        border_radius=12, filled=True, bgcolor="#FFFFFF",
        options=CAUTION_OPTIONS,
        value=_get_caution(),
        dense=True,
    )
    def on_site_change(e):
        price.disabled = bool(on_site.value); page.update()
    on_site.on_change = on_site_change
    def on_country(code: str):
        price.suffix_text = get_currency(code)

    geo = CountryCitySelector(page, existing_bien.get("country_code") if is_edit else user.get("country_code"), existing_bien.get("city") if is_edit else user.get("city"), on_country=on_country)
    locality = text_field(t("zone_label"), value=existing_bien.get("locality") if is_edit else user.get("locality") or "")
    description = text_field(t("description_label"), multiline=True, min_lines=3, max_lines=6, value=_get("description"))
    whatsapp = text_field(t("whatsapp_number_label"), value=existing_bien.get("whatsapp") if is_edit else user.get("phone") or "", keyboard_type=ft.KeyboardType.PHONE, prefix_icon=FT_ICONS.PHONE)
    # NOUVEAU: 2ème numéro
    whatsapp2 = text_field("2ème numéro(optionnel)", value=existing_bien.get("whatsapp2") or existing_bien.get("whatsapp_2") or "" if is_edit else "", keyboard_type=ft.KeyboardType.PHONE, prefix_icon=FT_ICONS.PHONE)

    photos_row = ft.Row(wrap=True, spacing=8, run_spacing=8)
    photos_title = ft.Text(f"{t('photos_label')} - {len(photos)}/{max_photos}", weight=ft.FontWeight.W_600)
    THUMB = 104
    photo_url = text_field(t("photo_url_label"))

    def render_photos():
        photos_title.value = f"{t('photos_label')} - {len(photos)}/{max_photos}"
        photos_row.controls = [
            ft.Stack([
                ft.Container(content=ft.Image(**image_kwargs(u), width=THUMB, height=THUMB, fit=ft.ImageFit.COVER, error_content=ft.Container(bgcolor="#DDE4DF")), width=THUMB, height=THUMB, border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE),
                ft.Container(content=ft.IconButton(FT_ICONS.CLOSE, icon_size=14, icon_color="#FFFFFF", bgcolor="#99000000", on_click=lambda e, x=u: remove_photo(x)), alignment=ft.alignment.top_right),
            ], width=THUMB, height=THUMB) for u in photos
        ]
        page.update()

    def remove_photo(u):
        photos.remove(u); render_photos()
    def add_photo_from_url(e):
        u = (photo_url.value or "").strip()
        if not u: return
        if len(photos) >= max_photos:
            snack(page, t("max_photos", n=max_photos), error=True); return
        photos.append(u); photo_url.value = ""; render_photos()
    def on_files(paths: List[str]):
        for path in paths:
            if len(photos) >= max_photos:
                snack(page, t("max_photos", n=max_photos), error=True); break
            try:
                photos.append(db.upload_photo(path))
            except Exception as ex:
                snack(page, t("upload_failed", err=ex), error=True)
        render_photos()

    picker = ImagePicker(page, "publish", on_files, multiple=True, limit=lambda: max_photos - len(photos), on_overflow=lambda: snack(page, t("max_photos", n=max_photos), error=True))

    def required(value, label_key) -> bool:
        if _digits(value) == "":
            snack(page, t("required_field", field=t(label_key)), error=True); return False
        return True

    def do_publish(e):
        kind = kind_dd.value; tx = transaction_dd.value
        if not (title.value or "").strip():
            snack(page, t("title_required"), error=True); return
        extra = {}
        if kind == CAT_MAISON:
            if not required(rooms.value, "rooms_label"): return
            if not required(showers.value, "showers_label"): return
            if not required(living.value, "living_rooms_label"): return
            if int(_digits(rooms.value)) < 1:
                snack(page, t("rooms_min_one"), error=True); return
            extra = {"chambres": int(_digits(rooms.value)), "salles_de_bain": int(_digits(showers.value)), "salons": int(_digits(living.value))}
            if has_cuisine.value:
                if not (cuisine_interne.value or cuisine_externe.value):
                    snack(page, "Choisis au moins cuisine interne ou externe", error=True); return
                extra["cuisine_interne"] = bool(cuisine_interne.value)
                extra["cuisine_externe"] = bool(cuisine_externe.value)
                if cuisine_interne.value and cuisine_externe.value: extra["cuisine_type"] = "Int + Ext"
                elif cuisine_interne.value: extra["cuisine_type"] = "Interne"
                else: extra["cuisine_type"] = "Externe"
                extra["cuisines"] = 1; extra["nb_cuisines"] = 1
            else:
                extra["cuisines"] = 0; extra["nb_cuisines"] = 0; extra["cuisine_type"] = ""
        elif kind == CAT_TERRAIN:
            if not _digits(surface.value) or int(_digits(surface.value)) <= 0:
                snack(page, t("surface_required"), error=True); return
        surface_val = _opt_int(surface.value)
        if surface_val is not None: extra["superficie"] = surface_val
        prix = None
        if not on_site.value:
            if not _digits(price.value):
                snack(page, t("price_required"), error=True); return
            prix = int(_digits(price.value))
            if prix > PG_INT_MAX:
                snack(page, t("invalid_price"), error=True); return
        if not geo.city:
            snack(page, t("country_city_required"), error=True); return
        if not (locality.value or "").strip():
            snack(page, t("zone_required_publish"), error=True); return
        if not (whatsapp.value or "").strip():
            snack(page, t("whatsapp_required"), error=True); return
        if not photos:
            snack(page, t("photo_required"), error=True); return
        # Recup avance / caution
        try:
            avance_val = int(avance_dd.value or 0)
        except:
            avance_val = 0
        try:
            caution_val = int(caution_dd.value or 0)
        except:
            caution_val = 0
        
        payload = {
            "titre": title.value.strip(), "type_bien": build_type_bien(tx, kind),
            "transaction": tx, "categorie": kind, "country_code": geo.country_code, "city": geo.city,
            "locality": locality.value.strip(), "prix": prix, "prix_discutable": bool(negotiable.value),
            "prix_sur_place": bool(on_site.value), "whatsapp": whatsapp.value.strip(),
            "whatsapp2": (whatsapp2.value or "").strip() or None,
            "description": (description.value or "").strip(), "photos": list(photos),
            "avance_mois": avance_val,
            "caution_mois": caution_val,
            "avance": avance_val,
            "caution": caution_val,
            **extra,
        }
        # Si edition: supprime les photos retirées
        if is_edit and existing_bien:
            old_photos = set(existing_bien.get("photos", []) or [])
            new_photos = set(payload.get("photos", []) or [])
            removed = old_photos - new_photos
            for photo_url in removed:
                try:
                    # Supprime fichier physique
                    if photo_url.startswith("http"):
                        from urllib.parse import urlparse
                        fname = Path(urlparse(photo_url).path).name
                        if db.mode == "supabase" and db.client:
                            try:
                                db.client.storage.from_("biens").remove([fname])
                            except:
                                pass
                        local = db.LOCAL_UPLOAD_DIR if hasattr(db, 'LOCAL_UPLOAD_DIR') else Path("assets/uploads")
                        # essaye suppression locale
                        for cand in [Path("assets/uploads") / fname, Path("uploads") / fname, LOCAL_UPLOAD_DIR / fname if 'LOCAL_UPLOAD_DIR' in globals() else Path(fname)]:
                            if cand.exists():
                                cand.unlink()
                    else:
                        for cand in [Path(photo_url), Path("assets") / photo_url, Path("assets/uploads") / Path(photo_url).name, Path("uploads") / Path(photo_url).name]:
                            if cand.exists() and cand.is_file():
                                cand.unlink()
                                break
                    print(f"[Edit] Photo retirée supprimée: {photo_url}")
                except Exception as e:
                    print(f"[Edit] Echec suppression photo retirée {photo_url}: {e}")

        try:
            if is_edit:
                db.update_bien(bien_id, payload)
                snack(page, "Annonce modifiée avec succès")
            else:
                payload["user_id"] = user["id"]
                db.create_bien(payload)
                snack(page, t("publish_success"))
            page.go("/mes-annonces" if is_edit else "/home")
        except Exception as ex:
            print(f"[PUBLISH] {ex}"); snack(page, t("publish_error", err=ex), error=True); return

    def bloc(controls):
        return ft.Container(bgcolor="#FFFFFF", border_radius=16, padding=14, border=ft.border.all(1, "#E0E4E1"), content=ft.Column(controls, spacing=10))

    # LAYOUT RESPONSIVE
    if is_desktop:
        left_col = ft.Column(spacing=12, controls=[
            bloc([title, ft.Row([ft.Container(transaction_dd, expand=True), ft.Container(kind_dd, expand=True)], spacing=8)]),
            bloc([house_row, ft.Divider(height=1, color="#EEEEEE"), cuisine_bloc, surface]),
            bloc([*geo.controls, locality]),
        ], expand=1)
        right_col = ft.Column(spacing=12, controls=[
            bloc([price, negotiable, on_site, ft.Divider(height=1, color="#EEEEEE"), ft.Text("Conditions location (Cameroun)", weight=ft.FontWeight.BOLD, size=13, color=COLORS["primary"]), ft.Row([ft.Container(avance_dd, expand=True), ft.Container(caution_dd, expand=True)], spacing=8)]),
            bloc([description, whatsapp, whatsapp2]),
            bloc([photos_title, photos_row, ft.OutlinedButton(t("upload_photo_button"), icon=FT_ICONS.ADD_A_PHOTO_OUTLINED, on_click=picker.open), ft.Row([ft.Container(photo_url, expand=True), ft.IconButton(FT_ICONS.ADD_CIRCLE, icon_color=COLORS["primary"], tooltip=t("add_button"), on_click=add_photo_from_url)])]),
            primary_button("Modifier" if is_edit else t("publish_button"), do_publish, FT_ICONS.CHECK if not is_edit else FT_ICONS.EDIT, expand=True),
        ], expand=1)
        form_content = ft.Row(spacing=16, controls=[left_col, right_col], vertical_alignment=ft.CrossAxisAlignment.START)
        wrapped = responsive_wrapper(form_content, width=1100, padding=20)
    else:
        form_content = ft.Column(spacing=12, controls=[
            bloc([title, transaction_dd, kind_dd]),
            bloc([house_row, ft.Divider(height=1, color="#EEEEEE"), cuisine_bloc, surface]),
            bloc([*geo.controls, locality]),
            bloc([price, negotiable, on_site, ft.Divider(height=1, color="#EEEEEE"), ft.Text("Conditions location (Cameroun)", weight=ft.FontWeight.BOLD, size=13, color=COLORS["primary"]), ft.Row([ft.Container(avance_dd, expand=True), ft.Container(caution_dd, expand=True)], spacing=8)]),
            bloc([description, whatsapp, whatsapp2]),
            bloc([photos_title, photos_row, ft.OutlinedButton(t("upload_photo_button"), icon=FT_ICONS.ADD_A_PHOTO_OUTLINED, on_click=picker.open), ft.Row([ft.Container(photo_url, expand=True), ft.IconButton(FT_ICONS.ADD_CIRCLE, icon_color=COLORS["primary"], tooltip=t("add_button"), on_click=add_photo_from_url)])]),
            primary_button("Modifier l'annonce" if is_edit else t("publish_button"), do_publish, FT_ICONS.EDIT if is_edit else FT_ICONS.CHECK, expand=True),
            ft.Container(height=30),
        ])
        wrapped = ft.Container(padding=12, content=form_content)

    return ft.View(route=f"/edit/{bien_id}" if is_edit else "/publish", bgcolor=COLORS["bg"], scroll=ft.ScrollMode.AUTO, appbar=ft.AppBar(leading=ft.IconButton(FT_ICONS.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/mes-annonces" if is_edit else "/home")), title=ft.Text("Modifier l'annonce" if is_edit else t("publish_title"), color="#FFFFFF", weight=ft.FontWeight.BOLD), bgcolor=COLORS["primary"]), controls=[wrapped])
