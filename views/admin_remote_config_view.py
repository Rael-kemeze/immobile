
"""Admin - Panneau controle a distance MODERNE - version stable."""

import flet as ft
from components.widgets import snack
from services.config import COLORS
from services.db import db
from services.remote_config import get_remote_config, clear_cache
import json
from pathlib import Path as PPath

def remote_config_view(page: ft.Page) -> ft.View:
    current = get_remote_config(force_refresh=True)
    
    PRIMARY = COLORS.get("primary", "#0F6B3E")
    PRIMARY_DARK = COLORS.get("primary_dark", "#0A4A2B")
    ACCENT = "#F59E0B"
    BG = COLORS.get("bg", "#F8FAF9")
    SURFACE = "#FFFFFF"
    MUTED = COLORS.get("muted", "#6B7280")
    
    # Fields
    latest_ver = ft.TextField(label="Version", value=current.get("latest_version","1.0.0"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True, expand=True)
    ver_code = ft.TextField(label="Code", value=str(current.get("version_code",100)), border_radius=12, filled=True, bgcolor=SURFACE, dense=True, width=100, keyboard_type=ft.KeyboardType.NUMBER)
    min_ver = ft.TextField(label="Version min", value=current.get("min_required_version","1.0.0"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True, expand=True)
    min_code = ft.TextField(label="Code min", value=str(current.get("min_required_code",100)), border_radius=12, filled=True, bgcolor=SURFACE, dense=True, width=100, keyboard_type=ft.KeyboardType.NUMBER)
    
    changelog = ft.TextField(label="Nouveautes", value=current.get("changelog",""), multiline=True, min_lines=2, max_lines=3, border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    update_msg = ft.TextField(label="Message MAJ douce", value=current.get("update_message","Nouvelle version disponible"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    force_msg = ft.TextField(label="Message MAJ obligatoire", value=current.get("force_update_message","Mise a jour obligatoire"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    maint_msg = ft.TextField(label="Message maintenance", value=current.get("maintenance_message","Maintenance en cours"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    
    mtn_num = ft.TextField(label="MTN MoMo", value=current.get("payment_methods",{}).get("mtn_number","6 70 12 34 56"), prefix_icon=ft.Icons.PHONE_ANDROID, border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    orange_num = ft.TextField(label="Orange Money", value=current.get("payment_methods",{}).get("orange_number","6 90 12 34 56"), prefix_icon=ft.Icons.PHONE, border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    wa_num = ft.TextField(label="WhatsApp", value=current.get("payment_methods",{}).get("whatsapp","6 70 12 34 56"), prefix_icon=ft.Icons.CHAT_BUBBLE, border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    
    apk_url = ft.TextField(label="URL APK", value=current.get("apk_url","https://immobile.cm/download/immobile.apk"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True)
    dl_url = ft.TextField(label="URL Site", value=current.get("download_url","https://immobile.cm"), border_radius=12, filled=True, bgcolor=SURFACE, dense=True)

    mon_switch = ft.Switch(value=bool(current.get("enable_monetization")), active_color=PRIMARY, thumb_color="white")
    boost_switch = ft.Switch(value=bool(current.get("enable_boost_only")), active_color=ACCENT)
    maint_switch = ft.Switch(value=bool(current.get("maintenance_mode")), active_color="#EF4444")

    status_monet = ft.Text("", size=11, weight=ft.FontWeight.BOLD)
    status_ver = ft.Text("", size=11, weight=ft.FontWeight.BOLD)
    
    def update_status():
        if mon_switch.value:
            status_monet.value = "ACTIF - Paiement ON"
            status_monet.color = "#16A34A"
        else:
            status_monet.value = "OFF - Gratuit"
            status_monet.color = MUTED
        try:
            latest = int(ver_code.value or 100)
            min_c = int(min_code.value or 100)
            if min_c >= latest and latest > 0:
                status_ver.value = "MAJ OBLIGATOIRE"
                status_ver.color = "#DC2626"
            elif latest > min_c:
                status_ver.value = f"MAJ dispo v{latest_ver.value}"
                status_ver.color = "#D97706"
            else:
                status_ver.value = "A jour"
                status_ver.color = "#16A34A"
        except:
            pass

    mon_switch.on_change = lambda e: (update_status(), page.update())
    ver_code.on_change = lambda e: (update_status(), page.update())
    min_code.on_change = lambda e: (update_status(), page.update())
    update_status()

    def save_config(e):
        try:
            payload = {
                "id": "main",
                "latest_version": latest_ver.value.strip(),
                "version_code": int(ver_code.value or 100),
                "min_required_version": min_ver.value.strip(),
                "min_required_code": int(min_code.value or 100),
                "enable_monetization": mon_switch.value,
                "enable_payments": mon_switch.value,
                "enable_boost_only": boost_switch.value,
                "maintenance_mode": maint_switch.value,
                "maintenance_message": maint_msg.value.strip(),
                "update_message": update_msg.value.strip(),
                "force_update_message": force_msg.value.strip(),
                "changelog": changelog.value.strip(),
                "apk_url": apk_url.value.strip(),
                "download_url": dl_url.value.strip(),
                "payment_methods": {
                    "mtn_number": mtn_num.value.strip(),
                    "orange_number": orange_num.value.strip(),
                    "whatsapp": wa_num.value.strip()
                },
                "updated_at": __import__("datetime").datetime.now().isoformat()
            }
            if db.mode == "supabase":
                res = db._safe_execute(db.client.table("app_config").select("id").eq("id","main").limit(1))
                if res.data:
                    db._safe_execute(db.client.table("app_config").update(payload).eq("id","main"))
                else:
                    db._safe_execute(db.client.table("app_config").insert(payload))
                clear_cache()
                snack(page, f"Sauvegarde OK ! v{payload['latest_version']} - {'ON' if mon_switch.value else 'OFF'}")
            else:
                p = PPath(__file__).parent.parent / "version.json"
                p.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
                clear_cache()
                snack(page, "Sauve local version.json")
            page.update()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)

    def quick_toggle(val, target):
        target.value = val
        update_status()
        page.update()

    def card(icon_name, title, subtitle, controls_list, accent):
        return ft.Container(
            bgcolor=SURFACE,
            border_radius=20,
            padding=18,
            shadow=ft.BoxShadow(blur_radius=20, color="#0F172A0D", offset=ft.Offset(0,4)),
            border=ft.border.all(1, "#F1F5F9"),
            content=ft.Column(spacing=14, controls=[
                ft.Row(spacing=12, controls=[
                    ft.Container(width=44, height=44, bgcolor=f"{accent}14", border_radius=12, alignment=ft.alignment.center, content=ft.Icon(icon_name, size=22, color=accent)),
                    ft.Column(expand=True, spacing=2, controls=[
                        ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color="#0F172A"),
                        ft.Text(subtitle, size=11, color=MUTED),
                    ])
                ]),
                ft.Column(spacing=10, controls=controls_list)
            ])
        )

    header = ft.Container(
        border_radius=20,
        padding=20,
        gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[PRIMARY, PRIMARY_DARK]),
        content=ft.Column(spacing=12, controls=[
            ft.Row(spacing=12, controls=[
                ft.Container(width=48, height=48, bgcolor="#FFFFFF22", border_radius=14, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.SETTINGS_REMOTE, color="white", size=26)),
                ft.Column(expand=True, spacing=2, controls=[
                    ft.Text("Controle a Distance", size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Text("Gere ton app sans republier", size=11, color="#CBD5E1"),
                ]),
                ft.Container(bgcolor="#FFFFFF", border_radius=20, padding=ft.padding.symmetric(10,14), content=ft.Row(spacing=6, controls=[
                    ft.Container(width=6, height=6, bgcolor="#22C55E", border_radius=3),
                    ft.Text(f"v{current.get('latest_version','1.0.0')}", size=12, weight=ft.FontWeight.BOLD, color="#0F172A"),
                ]))
            ]),
            ft.Row(spacing=8, controls=[
                ft.Container(expand=True, bgcolor="#FFFFFF15", border_radius=12, padding=10, content=ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.PEOPLE_OUTLINE, size=16, color="white"),
                    ft.Column(spacing=0, controls=[
                        ft.Text("Mode", size=10, color="#94A3B8"),
                        ft.Text("Payant" if current.get("enable_monetization") else "Gratuit", size=12, weight=ft.FontWeight.BOLD, color="white"),
                    ])
                ])),
                ft.Container(expand=True, bgcolor="#FFFFFF15", border_radius=12, padding=10, content=ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.PHONE_ANDROID, size=16, color="white"),
                    ft.Column(spacing=0, controls=[
                        ft.Text("APK", size=10, color="#94A3B8"),
                        ft.Text(f"Code {current.get('version_code',100)}", size=12, weight=ft.FontWeight.BOLD, color="white"),
                    ])
                ])),
            ])
        ])
    )

    card_monet = card(ft.Icons.PAYMENTS_ROUNDED, "Monetisation", "Active le paiement", [
        ft.Container(bgcolor="#F8FAFC", border_radius=12, padding=12, content=ft.Row(spacing=12, controls=[
            ft.Column(expand=True, spacing=4, controls=[
                ft.Text("Paiement / Paywall", size=13, weight=ft.FontWeight.W_600),
                ft.Text("OFF=illimite gratuit | ON=3 max + Boost 1000F", size=11, color=MUTED),
                status_monet,
            ]),
            mon_switch,
        ])),
        ft.Row(spacing=8, controls=[
            ft.Container(expand=True, content=ft.ElevatedButton("Activer", icon=ft.Icons.BOLT, style=ft.ButtonStyle(bgcolor=PRIMARY, color="white", shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda e: quick_toggle(True, mon_switch))),
            ft.Container(expand=True, content=ft.OutlinedButton("Desactiver", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)), on_click=lambda e: quick_toggle(False, mon_switch))),
        ]),
        ft.Container(bgcolor="#FFFBEB", border_radius=12, padding=12, border=ft.border.all(1, "#FDE68A"), content=ft.Row(spacing=10, controls=[
            ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=18, color="#D97706"),
            ft.Column(expand=True, spacing=2, controls=[
                ft.Text("Mode Boost seulement", size=12, weight=ft.FontWeight.BOLD, color="#92400E"),
                ft.Row(spacing=8, controls=[ft.Text("Gratuit + option Boost", size=11, color="#92400E", expand=True), boost_switch])
            ])
        ])),
    ], PRIMARY)

    card_versions = card(ft.Icons.SYSTEM_UPDATE_ROUNDED, "Versions APK", "Force les mises a jour", [
        ft.Row(spacing=10, controls=[latest_ver, ver_code]),
        ft.Row(spacing=10, controls=[min_ver, min_code]),
        status_ver,
        changelog,
        ft.Container(bgcolor="#F0FDF4", border_radius=10, padding=10, content=ft.Column(spacing=4, controls=[
            ft.Text("Comment forcer MAJ :", size=11, weight=ft.FontWeight.BOLD, color="#166534"),
            ft.Text("Code min = Code actuel => douce | Code min = Code latest => obligatoire", size=11, color="#166534"),
        ])),
        update_msg,
        force_msg,
    ], "#0EA5E9")

    card_pay = card(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, "Mobile Money", "Numeros affiches au paiement", [
        mtn_num, orange_num, wa_num,
    ], ACCENT)

    card_links = card(ft.Icons.LINK_ROUNDED, "Liens", "Distribution APK", [
        apk_url, dl_url,
    ], "#8B5CF6")

    card_maint = card(ft.Icons.BUILD_ROUNDED, "Maintenance", "Bloque l'app", [
        ft.Row(spacing=12, controls=[
            ft.Column(expand=True, spacing=4, controls=[ft.Text("Mode maintenance", size=13, weight=ft.FontWeight.W_600), ft.Text("Affiche ecran maintenance", size=11, color=MUTED)]),
            maint_switch,
        ]),
        maint_msg,
    ], "#EF4444")

    save_btn = ft.Container(
        border_radius=16,
        gradient=ft.LinearGradient(colors=[PRIMARY, PRIMARY_DARK], begin=ft.alignment.center_left, end=ft.alignment.center_right),
        shadow=ft.BoxShadow(blur_radius=20, color="#0F6B3E30", offset=ft.Offset(0,6)),
        content=ft.ElevatedButton(
            "Sauvegarder",
            icon=ft.Icons.SAVE_ROUNDED,
            style=ft.ButtonStyle(bgcolor="transparent", color="white", shadow_color="transparent", padding=ft.padding.symmetric(16,20), shape=ft.RoundedRectangleBorder(radius=16), text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD)),
            on_click=save_config,
            expand=True,
            height=54,
        )
    )

    content = ft.Column(spacing=16, scroll=ft.ScrollMode.AUTO, controls=[
        header,
        card_monet,
        card_versions,
        card_pay,
        card_links,
        card_maint,
        save_btn,
        ft.Container(height=30),
    ])

    return ft.View(
        route="/admin/remote",
        bgcolor=BG,
        padding=16,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(title=ft.Text("Controle a Distance", size=16, weight=ft.FontWeight.BOLD, color="white"), bgcolor=PRIMARY, elevation=0, leading=ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, icon_color="white", on_click=lambda e: page.go("/admin"))),
        controls=[content]
    )
