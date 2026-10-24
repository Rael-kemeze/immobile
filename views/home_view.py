"""Accueil : recherche, filtres (dont pays), liste des biens - RESPONSIVE FIX PC/TABLETTE."""

from __future__ import annotations
import flet as ft
from components.widgets import app_bar, bien_card, responsive_wrapper
from components.widgets import text_field
from services.auth import Session
from services.config import APP_CONFIG, CATEGORIES, COLORS, TRANSACTIONS
from services.countries import COUNTRIES, get_country, label, flag_image
from services.db import db
from services.monetization import monetization
from services.i18n import t

STATE = {
    "search": "",
    "categorie": None,
    "transaction": None,
    "city": None,
    "country_code": None,
    "prix_min": None,
    "prix_max": None,
    "prix_discutable": False,
    "country_init": False,
}

HOME_COUNTRY_KEY = "home_country"

def reset_home_state():
    STATE.update(
        search="",
        categorie=None,
        transaction=None,
        city=None,
        country_code=None,
        prix_min=None,
        prix_max=None,
        prix_discutable=False,
        country_init=False,
    )

def _transaction_chips():
    return [(t("filter_all"), None)] + [(t(f"tx_filter_{tr}"), tr) for tr in TRANSACTIONS]

def _category_chips():
    return [(t("filter_all"), None)] + [(t(f"category_{c}"), c) for c in CATEGORIES]

def home_view(page: ft.Page) -> ft.View:
    if not STATE["country_init"]:
        try:
            pref = page.client_storage.get(HOME_COUNTRY_KEY)
        except Exception:
            pref = None
        if pref == "ALL":
            STATE["country_code"] = None
        elif pref:
            STATE["country_code"] = pref
        elif Session.user:
            STATE["country_code"] = Session.user.get("country_code")
        STATE["country_init"] = True

    def open_bien(bien):
        page.go(f"/bien/{bien['id']}")

    # Conteneur résultats - sera GridView ou ListView selon taille
    results_container = ft.Container(expand=True)

    def refresh(e=None):
        raw_biens = db.list_biens(
            search=STATE["search"],
            categorie=STATE["categorie"],
            transaction=STATE["transaction"],
            city=STATE["city"],
            country_code=STATE["country_code"],
            prix_min=STATE["prix_min"],
            prix_max=STATE["prix_max"],
            prix_discutable=STATE["prix_discutable"],
            only_active=True,
        )
        biens = monetization.sort_biens_by_monetization(raw_biens)
        w = page.window_width or 400
        
        # Détermine colonnes selon largeur
        if w >= 1400:
            col_count = 4
            max_extent = 360
        elif w >= 1100:
            col_count = 3
            max_extent = 380
        elif w >= 700:
            col_count = 2
            max_extent = 400
        else:
            col_count = 1

        if not biens:
            results_container.content = ft.Container(
                padding=40,
                alignment=ft.alignment.center,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.SEARCH_OFF, size=56, color=COLORS["muted"]),
                        ft.Container(height=10),
                        ft.Text(t("no_results"), size=16, color=COLORS["muted"], text_align=ft.TextAlign.CENTER),
                    ]
                )
            )
        elif col_count == 1:
            # Mobile : liste verticale
            results_container.content = ft.ListView(
                expand=True,
                spacing=12,
                padding=ft.padding.only(bottom=80),
                controls=[bien_card(page, b, open_bien, refresh) for b in biens]
            )
        else:
            # Tablette / PC : grille
            results_container.content = ft.GridView(
                expand=True,
                runs_count=col_count,
                max_extent=max_extent,
                child_aspect_ratio=0.82,
                spacing=16,
                run_spacing=16,
                padding=ft.padding.only(bottom=80, top=4),
                controls=[bien_card(page, b, open_bien, refresh) for b in biens]
            )
        page.update()

    search = text_field(t("search_placeholder"), prefix_icon=ft.Icons.SEARCH)

    def on_search(e):
        STATE["search"] = (search.value or "").strip()
        refresh()

    search.on_change = on_search

    tx_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)
    cat_row = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=8)

    def select_tx(value):
        STATE["transaction"] = value
        build_chips()
        refresh()

    def select_cat(value):
        STATE["categorie"] = value
        build_chips()
        refresh()

    def chip(lbl, selected, on_click):
        return ft.Container(
            content=ft.Text(lbl, size=12, color="#FFFFFF" if selected else COLORS["text"], weight=ft.FontWeight.W_600),
            bgcolor=COLORS["primary"] if selected else "#FFFFFF",
            border=ft.border.all(1, "#DDE4DF"), border_radius=20,
            padding=ft.padding.symmetric(8, 14), on_click=on_click,
        )

    def build_chips():
        tx_row.controls = [chip(lbl, STATE["transaction"] == v, lambda e, v=v: select_tx(v)) for lbl, v in _transaction_chips()]
        cat_row.controls = [chip(lbl, STATE["categorie"] == v, lambda e, v=v: select_cat(v)) for lbl, v in _category_chips()]

    build_chips()

    country_options = [ft.dropdown.Option(key="ALL", content=ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.PUBLIC, size=18), ft.Text(t("all_countries"))]))] + [
        ft.dropdown.Option(
            key=c["code"],
            content=ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Image(src=c["flag_url"], width=24, height=18, fit=ft.ImageFit.COVER, border_radius=2),
                ft.Text(f"{c['name']} ({c['dial']})", size=13)
            ])
        ) for c in COUNTRIES
    ]

    def current_key():
        if STATE["country_code"] is None:
            return "ALL"
        return STATE["country_code"]

    country_dd = ft.Dropdown(border_radius=12, filled=True, bgcolor="#FFFFFF", options=country_options, value=current_key(), expand=True)

    def on_country_change(e):
        code = country_dd.value
        if code == "ALL":
            STATE["country_code"] = None
        else:
            STATE["country_code"] = code
        try:
            page.client_storage.set(HOME_COUNTRY_KEY, code)
        except:
            pass
        refresh()

    country_dd.on_change = on_country_change

    prix_min = text_field(t("price_min"), keyboard_type=ft.KeyboardType.NUMBER)
    prix_max = text_field(t("price_max"), keyboard_type=ft.KeyboardType.NUMBER)
    discutable = ft.Checkbox(label=t("negotiable_only"))

    def apply_filters(e):
        STATE["prix_min"] = int(prix_min.value) if (prix_min.value or "").isdigit() else None
        STATE["prix_max"] = int(prix_max.value) if (prix_max.value or "").isdigit() else None
        STATE["prix_discutable"] = discutable.value
        filters_panel.visible = False
        refresh()

    filters_panel = ft.Container(
        visible=False, bgcolor="#FFFFFF", border_radius=14, padding=12, margin=ft.margin.only(bottom=10),
        content=ft.Column(spacing=8, controls=[
            ft.Row([ft.Container(prix_min, expand=True), ft.Container(prix_max, expand=True)]),
            discutable,
            ft.ElevatedButton(t("apply_filters"), on_click=apply_filters, style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF")),
        ]),
    )

    def toggle_filters(e):
        filters_panel.visible = not filters_panel.visible
        page.update()

    # Header filtres - responsive : sur PC, tout sur une ligne
    def build_header():
        w = page.window_width or 400
        if w >= 900:
            # PC : barre filtres en ligne
            return ft.Column(spacing=10, controls=[
                ft.Row(spacing=10, controls=[
                    ft.Container(country_dd, width=280),
                    ft.Container(search, expand=True),
                    ft.IconButton(ft.Icons.TUNE, icon_color=COLORS["primary"], bgcolor="#FFFFFF", on_click=toggle_filters),
                ]),
                tx_row,
                cat_row,
                filters_panel,
            ])
        else:
            # Mobile : colonne
            return ft.Column(spacing=8, controls=[
                country_dd,
                ft.Row([ft.Container(search, expand=True), ft.IconButton(ft.Icons.TUNE, icon_color=COLORS["primary"], bgcolor="#FFFFFF", on_click=toggle_filters)]),
                tx_row, cat_row,
                filters_panel,
            ])

    header_container = ft.Container(content=build_header())

    def on_resize(e):
        header_container.content = build_header()
        refresh()

    page.on_resized = on_resize

    refresh()

    # Body principal - Column avec header fixe + résultats expand
    body = ft.Column(expand=True, spacing=0, controls=[
        header_container,
        ft.Container(height=10),
        results_container,
    ])

    w = page.window_width or 400
    if w >= 700:
        body_wrapped = ft.Container(
            alignment=ft.alignment.top_center,
            expand=True,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Container(content=body, width=1400, expand=True)
        )
    else:
        body_wrapped = ft.Container(padding=ft.padding.all(12), content=body, expand=True)

    return ft.View(
        route="/home",
        bgcolor=COLORS["bg"],
        appbar=app_bar(APP_CONFIG["APP_NAME"], page, actions=[
            ft.IconButton(ft.Icons.NOTIFICATIONS_OUTLINED, icon_color="#FFFFFF", on_click=lambda e: page.go("/notifications")),
            ft.IconButton(ft.Icons.REFRESH, icon_color="#FFFFFF", on_click=refresh),
        ] + ([ft.IconButton(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, icon_color="#FFFFFF", tooltip=t("admin_space"), on_click=lambda e: page.go("/admin"))] if Session.is_admin() else [])),
        controls=[body_wrapped],
        floating_action_button=ft.FloatingActionButton(icon=ft.Icons.ADD, bgcolor=COLORS["accent"], on_click=lambda e: page.go("/publish")),
        navigation_bar=bottom_bar(page, 0),
        padding=0,
    )

def bottom_bar(page: ft.Page, index: int) -> ft.NavigationBar:
    routes = ["/home", "/favoris", "/mes-annonces", "/profile"]
    def on_change(e):
        page.go(routes[e.control.selected_index])
    return ft.NavigationBar(
        selected_index=index, on_change=on_change, bgcolor="#FFFFFF", indicator_color="#D8EDE2",
        destinations=[
            ft.NavigationDestination(icon=ft.Icons.HOME_OUTLINED, label=t("nav_home")),
            ft.NavigationDestination(icon=ft.Icons.FAVORITE_BORDER, label=t("nav_favorites")),
            ft.NavigationDestination(icon=ft.Icons.LIST_ALT, label=t("nav_my_listings")),
            ft.NavigationDestination(icon=ft.Icons.PERSON_OUTLINE, label=t("nav_profile")),
        ],
    )

def empty_state(msg: str):
    return ft.Container(padding=30, alignment=ft.alignment.center, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Icon(ft.Icons.SEARCH_OFF, size=48, color=COLORS["muted"]), ft.Text(msg, color=COLORS["muted"])]))

def skeleton_card():
    return ft.Container(bgcolor="#FFFFFF", border_radius=16, padding=12, border=ft.border.all(1, "#E0E4E1"), content=ft.Column(controls=[ft.Container(height=120, bgcolor="#EEEEEE", border_radius=8), ft.Container(height=14, bgcolor="#EEEEEE", border_radius=4)]))
