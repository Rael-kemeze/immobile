"""Vue Premium - Achat de plans + Boost - Mobile Money Cameroun."""

from __future__ import annotations
import flet as ft
from components.widgets import app_bar, primary_button, snack
from services.auth import Session
from services.config import COLORS
from services.db import db
from services.monetization import PLANS, PAYMENT_METHODS, monetization, ENABLE_MONETIZATION, ENABLE_BOOST_ONLY, MY_MTN_NUMBER, MY_ORANGE_NUMBER

def premium_view(page: ft.Page) -> ft.View:
    if not Session.user:
        page.go("/login")
        return ft.View(route="/premium")

    user = Session.user
    current_plan = monetization.get_user_plan(user)
    credits = monetization.get_credits(user)
    
    # Compte annonces utilisateur
    try:
        my_biens = db.list_biens(user_id=user["id"])
        total_biens = len(my_biens)
    except:
        total_biens = 0
        my_biens = []

    def buy_plan(plan_id: str):
        plan = PLANS[plan_id]
        # Crée demande paiement
        payment = monetization.create_payment_request(user["id"], plan_id, "manual", plan["price"])
        
        # Pour MVP : on simule paiement direct + validation admin via WhatsApp
        # En prod : intégrer CinetPay / NotchPay / MoMo API
        
        # Ici on ouvre dialog paiement
        show_payment_dialog(plan, payment)

    def show_payment_dialog(plan, payment):
        # Dialog choix méthode paiement
        selected_method = {"id": "mtn"}
        
        method_radios = ft.RadioGroup(
            value="mtn",
            content=ft.Column(spacing=8, controls=[
                ft.Radio(value=m["id"], label=f"{m['icon']} {m['name']}") for m in PAYMENT_METHODS
            ])
        )
        
        def on_method_change(e):
            selected_method["id"] = method_radios.value
        
        method_radios.on_change = on_method_change
        
        transaction_field = ft.TextField(label="ID Transaction MoMo (optionnel)", hint_text="Ex: 123456789")
        
        def confirm_pay(e):
            method = selected_method["id"]
            # Enregistre demande
            try:
                # Simule paiement réussi pour démo - en prod vérifier via API
                # Pour MVP on crédite directement et admin valide après
                if plan["id"] == "BOOST":
                    # Si BOOST seul : on crédite 1 crédit sans changer plan
                    new_credits = (user.get("credits") or 0) + 1
                    db.update_user(user["id"], {"credits": new_credits})
                    user["credits"] = new_credits
                    snack(page, f"✅ Boost ajouté ! Tu as {new_credits} crédit(s)")
                else:
                    monetization.apply_plan_to_user(user, plan["id"], db)
                    snack(page, f"🎉 Bienvenue en {plan['name']} !")
                
                page.dialog.open = False
                page.update()
                page.go("/premium")
            except Exception as ex:
                snack(page, f"Erreur: {ex}", error=True)
        
        def close_dlg(e):
            page.dialog.open = False
            page.update()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Payer {plan['name']} - {plan['price']} FCFA"),
            content=ft.Column(spacing=12, tight=True, controls=[
                ft.Text(f"Plan {plan['name']} - {plan['price']} FCFA", weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("Choisis ta méthode:", weight=ft.FontWeight.W_600),
                method_radios,
                transaction_field,
                ft.Container(
                    bgcolor="#FFF3CD", padding=10, border_radius=8,
                    content=ft.Column(spacing=4, controls=[
                        ft.Text(f"📱 MTN MoMo: {PAYMENT_METHODS[0]['number']} - {PAYMENT_METHODS[0].get('owner','')}", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(f"🟠 Orange Money: {PAYMENT_METHODS[1]['number']} - {PAYMENT_METHODS[1].get('owner','')}", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(f"💬 WhatsApp: {PAYMENT_METHODS[2]['number']}", size=12, weight=ft.FontWeight.BOLD),
                        ft.Text("Envoie le montant puis entre l'ID transaction", size=11, color=COLORS["muted"]),
                        ft.Text("Ou contacte nous sur WhatsApp pour validation manuelle", size=11, color=COLORS["muted"]),
                    ])
                )
            ]),
            actions=[
                ft.TextButton("Annuler", on_click=close_dlg),
                ft.ElevatedButton("J'ai payé", on_click=confirm_pay, style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF")),
            ]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def plan_card(plan_id: str):
        plan = PLANS[plan_id]
        is_current = current_plan["id"] == plan_id
        is_popular = plan_id == "PRO"
        
        features = [ft.Row(spacing=6, controls=[
            ft.Icon(ft.icons.CHECK_CIRCLE, size=16, color=COLORS["primary"]),
            ft.Text(f, size=12, color=COLORS["text"], expand=True)
        ]) for f in plan["features"]]
        
        return ft.Container(
            width=320,
            bgcolor="#FFFFFF",
            border_radius=16,
            border=ft.border.all(2, plan["color"] if is_current else "#E0E4E1"),
            padding=16,
            shadow=ft.BoxShadow(blur_radius=10, color="#1A00000D") if is_popular else None,
            content=ft.Column(spacing=10, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Container(
                        bgcolor=f"{plan['color']}15",
                        padding=ft.padding.symmetric(6,10),
                        border_radius=20,
                        content=ft.Row(spacing=4, controls=[
                            ft.Icon(getattr(ft.icons, plan["icon"], ft.icons.STAR), size=16, color=plan["color"]),
                            ft.Text(plan["name"], size=12, weight=ft.FontWeight.BOLD, color=plan["color"]),
                        ])
                    ),
                    ft.Container(
                        visible=is_popular,
                        bgcolor=COLORS["accent"], padding=ft.padding.symmetric(4,8), border_radius=12,
                        content=ft.Text("POPULAIRE", size=10, weight=ft.FontWeight.BOLD, color="#000000")
                    ) if is_popular else ft.Container(),
                    ft.Container(
                        visible=is_current,
                        bgcolor=COLORS["primary"], padding=ft.padding.symmetric(4,8), border_radius=12,
                        content=ft.Text("ACTIF", size=10, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                    ) if is_current else ft.Container(),
                ]),
                ft.Text(f"{plan['price']} FCFA" if plan['price']>0 else "Gratuit", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text"]),
                ft.Text(f"{'par mois' if plan_id in ('PRO','PREMIUM') else 'pour 7 jours' if plan_id=='BOOST' else 'pour toujours'}", size=11, color=COLORS["muted"]),
                ft.Divider(height=1, color="#EEEEEE"),
                ft.Column(spacing=6, controls=features),
                ft.Container(height=6),
                ft.ElevatedButton(
                    "Plan actuel" if is_current else f"Choisir {plan['name']}",
                    disabled=is_current,
                    on_click=lambda e, pid=plan_id: buy_plan(pid),
                    style=ft.ButtonStyle(
                        bgcolor=plan["color"] if not is_current else "#E0E4E1",
                        color="#FFFFFF" if not is_current else COLORS["muted"],
                        shape=ft.RoundedRectangleBorder(radius=12)
                    ),
                    expand=True,
                    height=44,
                )
            ])
        )

    # Header crédits
    header = ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=16, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=10, controls=[
                ft.Container(width=48, height=48, bgcolor=f"{current_plan['color']}15", border_radius=12, alignment=ft.alignment.center,
                    content=ft.Icon(getattr(ft.icons, current_plan["icon"], ft.icons.STAR), color=current_plan["color"], size=24)),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text(f"Plan {current_plan['name']}", weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(f"{credits} crédit(s) Boost • {total_biens} annonces", size=12, color=COLORS["muted"]),
                ]),
                ft.IconButton(ft.icons.REFRESH, icon_color=COLORS["primary"], on_click=lambda e: page.go("/premium")),
            ]),
            ft.Container(
                visible=current_plan["id"]=="FREE",
                bgcolor="#FFF3CD", padding=10, border_radius=8,
                content=ft.Text(f"Il te reste {monetization.get_free_remaining(user, total_biens)} annonces gratuites", size=12, color="#856404")
            )
        ])
    )

    plans_row = ft.Row(
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
        controls=[plan_card(pid) for pid in ["FREE", "BOOST", "PRO", "PREMIUM"]]
    )

    # Section comment gagner
    how_to = ft.Container(
        bgcolor="#FFFFFF", border_radius=16, padding=16, border=ft.border.all(1, "#E0E4E1"),
        content=ft.Column(spacing=10, controls=[
            ft.Text("💰 Comment gagner de l'argent avec IMMOBILE ?", weight=ft.FontWeight.BOLD, size=15),
            ft.Column(spacing=8, controls=[
                ft.Row(spacing=8, controls=[ft.Text("1️⃣", size=16), ft.Text("Frais de publication : 500 FCFA après 3 annonces gratuites", size=13, expand=True)]),
                ft.Row(spacing=8, controls=[ft.Text("2️⃣", size=16), ft.Text("Boost 1000 FCFA = ton annonce en tête pendant 7 jours (x5 vues)", size=13, expand=True)]),
                ft.Row(spacing=8, controls=[ft.Text("3️⃣", size=16), ft.Text("Abonnement Agence 5000 FCFA/mois = annonces illimitées + badge PRO", size=13, expand=True)]),
                ft.Row(spacing=8, controls=[ft.Text("4️⃣", size=16), ft.Text("Commission : tu peux prendre 10% si tu fais l'intermédiaire", size=13, expand=True)]),
            ]),
            ft.Container(
                bgcolor="#E8F5E9", padding=12, border_radius=10,
                content=ft.Column(spacing=4, controls=[
                    ft.Text("💡 Exemple de revenus:", weight=ft.FontWeight.BOLD, size=13),
                    ft.Text("• 100 utilisateurs PRO x 5000 FCFA = 500 000 FCFA/mois", size=12),
                    ft.Text("• 200 Boosts x 1000 FCFA = 200 000 FCFA/mois", size=12),
                    ft.Text("• Total potentiel : 700 000 FCFA/mois avec 1000 users", size=12, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                ])
            )
        ])
    )

    # Banner mode gratuit
    mode_banner = ft.Container(
        visible=not ENABLE_MONETIZATION,
        bgcolor="#E3F2FD",
        padding=12,
        border_radius=12,
        border=ft.border.all(1, "#90CAF9"),
        content=ft.Column(spacing=4, controls=[
            ft.Row(spacing=6, controls=[
                ft.Icon(ft.icons.INFO_OUTLINED, size=18, color="#1565C0"),
                ft.Text("Mode Lancement Gratuit Activé", weight=ft.FontWeight.BOLD, size=13, color="#0D47A1"),
            ]),
            ft.Text("Tout est gratuit pour l'instant pour attirer les premiers utilisateurs. Passe ENABLE_MONETIZATION = True quand tu veux activer le paiement.", size=11, color="#1565C0"),
        ])
    )

    content = ft.Column(spacing=14, controls=[
        mode_banner,
        header,

        ft.Text("Choisis ton plan", weight=ft.FontWeight.BOLD, size=18),
        plans_row,
        how_to,
        ft.Container(height=20),
    ])

    return ft.View(
        route="/premium",
        bgcolor=COLORS["bg"],
        scroll=ft.ScrollMode.AUTO,
        appbar=app_bar("Premium & Gains", page, show_back=True),
        controls=[ft.Container(padding=14, content=content)],
    )
