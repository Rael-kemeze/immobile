"""Vue détails - 2 numéros visibles + appel + WhatsApp pré-rempli."""

from __future__ import annotations
from typing import Any, Dict
import flet as ft

from components.widgets import app_bar, badge, format_prix, image_kwargs, type_label, whatsapp_button, phone_row, snack, admin_actions, flag_image, primary_button, outline_button, wa_url, call_url
from services.auth import Session
from services.config import COLORS
from services.countries import get_country, label as country_label
from services.db import db
from services.i18n import t

def _spec_item(icon: str, label: str, value: Any, color: str = "#0F6B3F"):
    if value is None or value == "":
        display = "0"
    else:
        try:
            if isinstance(value, bool):
                display = "1" if value else "0"
            else:
                display = str(int(value))
        except:
            display = str(value) if str(value).strip() != "" else "0"
    return ft.Container(
        expand=True, bgcolor="#F6F8F7", border_radius=12, padding=12,
        border=ft.border.all(1, "#E8EDE9"),
        content=ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Icon(icon, size=26, color=color),
            ft.Text(display, size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Text(label, size=11, color=COLORS["muted"], text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500),
        ]),
    )

def detail_view(page: ft.Page, bien_id: str) -> ft.View:
    bien = db.get_bien(bien_id)
    if not bien:
        return ft.View(route=f"/bien/{bien_id}", controls=[ft.Text(t("not_found"))])

    is_desktop = (page.window_width or 0) >= 900
    is_owner = Session.user and bien.get("user_id") == Session.user["id"]
    is_admin = Session.is_admin()

    photos = bien.get("photos") or [None]
    main_img = ft.Image(**image_kwargs(photos[0]), width=800, height=420 if is_desktop else 220, fit=ft.ImageFit.COVER, border_radius=12)

    def update_main(idx: int):
        kwargs = image_kwargs(photos[idx])
        if "src_base64" in kwargs:
            main_img.src_base64 = kwargs["src_base64"]; main_img.src = None
        else:
            main_img.src = kwargs.get("src"); main_img.src_base64 = None
        for i, thumb in enumerate(thumbs.controls):
            thumb.border = ft.border.all(2.5, COLORS["primary"] if i == idx else "#E0E4E1")
        page.update()

    thumbs = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)
    for i, p in enumerate(photos[:10]):
        c = ft.Container(width=72, height=56, border_radius=8, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.border.all(2.5, COLORS["primary"] if i == 0 else "#E0E4E1"),
            content=ft.Image(**image_kwargs(p), width=72, height=56, fit=ft.ImageFit.COVER),
            on_click=lambda e, idx=i: update_main(idx))
        thumbs.controls.append(c)

    def get_val(*keys):
        for k in keys:
            v = bien.get(k)
            if v is not None and str(v).strip() != "":
                return v
        return 0

    nb_chambres = get_val("chambres", "nb_chambres", "rooms")
    nb_douches = get_val("salles_de_bain", "nb_douches", "douches", "sdb")
    nb_salons = get_val("salons", "nb_salons", "salon")
    
    # LOGIQUE CUISINE ROBUSTE: vérifie toutes les variantes possibles
    cuisine_interne = bien.get("cuisine_interne")
    cuisine_externe = bien.get("cuisine_externe")
    cuisine_type = (bien.get("cuisine_type") or bien.get("type_cuisine") or "").strip()
    cuisines_raw = bien.get("cuisines")
    nb_cuisines_raw = bien.get("nb_cuisines")
    
    # Normalise booléens (peut être True, "true", 1, "1")
    def is_true(v):
        if v is True: return True
        if isinstance(v, (int, float)): return v != 0
        if isinstance(v, str): return v.lower() in ("true", "1", "t", "yes", "interne", "externe")
        return False
    
    has_interne = is_true(cuisine_interne)
    has_externe = is_true(cuisine_externe)
    
    # Détermine affichage
    if has_interne and has_externe:
        nb_cuisines_display = "Int + Ext"
        nb_cuisines_val = 1
    elif has_interne:
        nb_cuisines_display = "Interne"
        nb_cuisines_val = 1
    elif has_externe:
        nb_cuisines_display = "Externe"
        nb_cuisines_val = 1
    elif cuisine_type:
        nb_cuisines_display = cuisine_type
        nb_cuisines_val = 1
    else:
        # Fallback sur cuisines count
        val = cuisines_raw if cuisines_raw is not None else nb_cuisines_raw
        try:
            nb_cuisines_val = int(val) if val is not None and str(val).strip() != "" else 0
        except:
            nb_cuisines_val = 0
        nb_cuisines_display = str(nb_cuisines_val)

    def _cuisine_item():
        # Si c'est du texte comme "Interne", affiche joli
        if isinstance(nb_cuisines_display, str) and nb_cuisines_display and not nb_cuisines_display.isdigit():
            return ft.Container(expand=True, bgcolor="#FFF3E0", border_radius=12, padding=12, border=ft.border.all(1, "#FFE0B2"),
                content=ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.icons.KITCHEN_OUTLINED, size=26, color="#E76F51"),
                    ft.Text(nb_cuisines_display, size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"], text_align=ft.TextAlign.CENTER),
                    ft.Text("Cuisine", size=11, color=COLORS["muted"]),
                ]))
        else:
            return _spec_item(ft.icons.KITCHEN_OUTLINED, "Cuisines", nb_cuisines_val, "#E76F51")

    def _cuisine_item():
        if isinstance(nb_cuisines_display, str) and not nb_cuisines_display.isdigit():
            return ft.Container(expand=True, bgcolor="#FFF3E0", border_radius=12, padding=12, border=ft.border.all(1, "#FFE0B2"),
                content=ft.Column(spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.icons.KITCHEN_OUTLINED, size=26, color="#E76F51"),
                    ft.Text(nb_cuisines_display, size=14, weight=ft.FontWeight.BOLD, color=COLORS["text"], text_align=ft.TextAlign.CENTER),
                    ft.Text("Cuisine", size=11, color=COLORS["muted"]),
                ]))
        else:
            return _spec_item(ft.icons.KITCHEN_OUTLINED, "Cuisines", nb_cuisines_val, "#E76F51")

    spec_row1 = ft.Row(spacing=10, controls=[
        _spec_item(ft.icons.BED_OUTLINED, "Chambres", nb_chambres, "#0F6B3F"),
        _spec_item(ft.icons.BATHTUB_OUTLINED, "Douches", nb_douches, "#1976D2"),
    ])
    spec_row2 = ft.Row(spacing=10, controls=[
        _spec_item(ft.icons.WEEKEND_OUTLINED, "Salons", nb_salons, "#6A4C93"),
        _cuisine_item(),
    ])

    country = get_country(bien.get("country_code"))
    location_row = ft.Row(spacing=6, controls=[
        ft.Icon(ft.icons.LOCATION_ON_OUTLINED, size=16, color=COLORS["muted"]),
        flag_image(bien.get("country_code", "CM"), size=16),
        ft.Text(f"{bien.get('city','')} - {bien.get('locality','')} • {country_label(country)}", size=12, color=COLORS["muted"]),
    ])

    def toggle_fav(e):
        if not Session.user: page.go("/login"); return
        if db.is_favori(Session.user["id"], bien["id"]):
            db.remove_favori(Session.user["id"], bien["id"]); snack(page, t("removed_fav"))
        else:
            db.add_favori(Session.user["id"], bien["id"]); snack(page, t("added_fav"))
        page.update()

    is_fav = db.is_favori(Session.user["id"], bien["id"]) if Session.user else False
    admin_row = admin_actions(page, bien, on_changed=lambda: page.go("/home"))

    gallery = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=8, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=8, controls=[
            ft.Container(border_radius=12, clip_behavior=ft.ClipBehavior.ANTI_ALIAS, content=main_img),
            thumbs if len(photos) > 1 else ft.Container(),
        ]))

    title_bloc = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=8, controls=[
                badge(type_label(bien), COLORS["primary"]),
                badge(bien.get("transaction",""), COLORS["accent"], "#000000") if bien.get("transaction") else ft.Container(),
                flag_image(bien.get("country_code","CM"), size=20),
            ]),
            ft.Text(bien.get("titre",""), size=20, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
            ft.Text(format_prix(bien), size=22, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
            location_row,
        ]))

    # === NOUVEAU: Avance & Caution ===
    avance_val = bien.get("avance_mois") or bien.get("avance") or 0
    caution_val = bien.get("caution_mois") or bien.get("caution") or 0
    try:
        avance_val = int(avance_val)
    except:
        avance_val = 0
    try:
        caution_val = int(caution_val)
    except:
        caution_val = 0
    
    conditions_controls = []
    if avance_val > 0 or caution_val > 0:
        cond_items = []
        if avance_val > 0:
            cond_items.append(ft.Container(
                expand=True, bgcolor="#E8F5E9", border_radius=12, padding=12, border=ft.border.all(1, "#C8E6C9"),
                content=ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.icons.CALENDAR_MONTH_OUTLINED, size=24, color=COLORS["primary"]),
                    ft.Text(f"{avance_val} mois", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Text("Avance", size=11, color=COLORS["muted"]),
                ])
            ))
        if caution_val > 0:
            cond_items.append(ft.Container(
                expand=True, bgcolor="#FFF3E0", border_radius=12, padding=12, border=ft.border.all(1, "#FFE0B2"),
                content=ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Icon(ft.icons.SECURITY_OUTLINED, size=24, color="#E76F51"),
                    ft.Text(f"{caution_val} mois", size=18, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                    ft.Text("Caution", size=11, color=COLORS["muted"]),
                ])
            ))
        # Calcul total si prix dispo
        if bien.get("prix") and (avance_val + caution_val) > 0:
            try:
                prix = int(bien.get("prix"))
                total = prix * (avance_val + caution_val)
                cond_items.append(ft.Container(
                    expand=True, bgcolor="#E3F2FD", border_radius=12, padding=12, border=ft.border.all(1, "#BBDEFB"),
                    content=ft.Column(spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Icon(ft.icons.PAYMENTS_OUTLINED, size=24, color="#1976D2"),
                        ft.Text(f"{total:,}".replace(","," "), size=16, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                        ft.Text(f"Total entrée ({avance_val+caution_val} mois)", size=10, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
                    ])
                ))
            except:
                pass
        
        if cond_items:
            conditions_bloc = ft.Container(
                bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
                content=ft.Column(spacing=10, controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.icons.RECEIPT_LONG_OUTLINED, size=18, color=COLORS["primary"]),
                        ft.Text("Conditions de location", weight=ft.FontWeight.BOLD, size=15),
                    ]),
                    ft.Row(spacing=10, controls=cond_items),
                    ft.Container(
                        bgcolor="#F8FAFC", border_radius=8, padding=8,
                        content=ft.Text(f"À payer à l'entrée : {avance_val} mois d'avance + {caution_val} mois de caution = {avance_val+caution_val} mois au total" if avance_val or caution_val else "", size=11, color=COLORS["muted"])
                    ) if (avance_val or caution_val) else ft.Container(),
                ])
            )
        else:
            conditions_bloc = ft.Container()
    else:
        conditions_bloc = ft.Container()

    specs_bloc = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=10, controls=[
            ft.Text("Caractéristiques", weight=ft.FontWeight.BOLD, size=15), spec_row1, spec_row2,
        ]))

    desc_bloc = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=6, controls=[
            ft.Text("Description", weight=ft.FontWeight.BOLD, size=15),
            ft.Text(bien.get("description","") or "Pas de description", size=13, color=COLORS["text"]),
        ]))

    # Gestion 2 numeros avec affichage + appel + WhatsApp pré-rempli
    wa1 = bien.get("whatsapp") or bien.get("user_phone") or ""
    wa2 = bien.get("whatsapp2") or bien.get("whatsapp_2") or ""

    contact_controls = []
    if wa1:
        contact_controls.append(phone_row(page, wa1, "Numéro 1" if wa2 else "Contact", bien))
    if wa2:
        contact_controls.append(phone_row(page, wa2, "Numéro 2", bien))

    if not contact_controls:
        contact_controls = [ft.Text("Aucun numéro disponible", color=COLORS["muted"])]

    contact_bloc = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=10, controls=[
            ft.Text("Contacter le propriétaire", weight=ft.FontWeight.BOLD, size=15),
            *contact_controls,
        ]))

    action_bloc = ft.Container(bgcolor="#FFFFFF", border_radius=14, padding=14, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=10, controls=[
            ft.Row(spacing=10, controls=[
                ft.Container(expand=True, content=ft.IconButton(icon=ft.icons.FAVORITE if is_fav else ft.icons.FAVORITE_BORDER, icon_color="#FF3B30", bgcolor="#FFF0F0", on_click=toggle_fav)),
                ft.Container(expand=True, content=ft.ElevatedButton(
                    "Modifier mon annonce",
                    icon=ft.icons.EDIT,
                    visible=is_owner or is_admin,
                    on_click=lambda e: page.go(f"/edit/{bien['id']}"),
                    style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF", shape=ft.RoundedRectangleBorder(radius=12)),
                    height=44,
                )) if is_owner or is_admin else ft.Container(expand=True),
            ]),
            admin_row if admin_row else ft.Container(),
        ]))

    if is_desktop:
        left = ft.Column(spacing=12, controls=[gallery, desc_bloc, contact_bloc], expand=2)
        right = ft.Column(spacing=12, controls=[title_bloc, specs_bloc, conditions_bloc, action_bloc], expand=1)
        main_row = ft.Row(spacing=16, controls=[left, right], vertical_alignment=ft.CrossAxisAlignment.START)
        content = ft.Container(
            alignment=ft.alignment.top_center,
            padding=ft.padding.all(20),
            content=ft.Container(width=1200, content=main_row)
        )
    else:
        content = ft.Container(
            padding=ft.padding.all(12),
            content=ft.Column(spacing=12, controls=[
                gallery, title_bloc, specs_bloc, conditions_bloc, desc_bloc, contact_bloc, action_bloc,
                ft.Container(height=80)
            ])
        )

    return ft.View(
        route=f"/bien/{bien_id}",
        bgcolor=COLORS["bg"],
        appbar=app_bar(bien.get("titre","")[:22], page, show_back=True),
        controls=[content],
        scroll=ft.ScrollMode.AUTO,
        padding=0,
    )
