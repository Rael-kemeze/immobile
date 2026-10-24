"""Admin - Gestion base de données et stockage."""

import flet as ft
from components.widgets import primary_button, snack
from services.config import COLORS
from services.db import db

def maintenance_view(page: ft.Page) -> ft.View:
    stats_text = ft.Text("Chargement...", size=12)
    progress = ft.ProgressBar(visible=False)
    
    def refresh_stats(e=None):
        progress.visible = True
        page.update()
        try:
            stats = db.get_database_stats()
            
            # Construit le rapport
            import os
            is_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
            cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
            
            if is_cloudinary:
                lines = [
                    f"Mode: {stats.get('mode')} + CLOUDINARY ({cloud_name})",
                    f"Biens total: {stats.get('biens_total', 0)} (actifs: {stats.get('biens_total',0) - stats.get('biens_inactifs',0)}, inactifs: {stats.get('biens_inactifs',0)})",
                    f"Utilisateurs: {stats.get('users_total',0)}",
                    f"Favoris: {stats.get('favoris_total',0)}",
                    f"Notifications: {stats.get('notifications_total',0)}",
                    f"Alertes: {stats.get('alerts_total',0)}",
                    f"OTP codes: {stats.get('otp_codes_total',0)}",
                    f"",
                    f"STOCKAGE CLOUDINARY (25 Go gratuit):",
                    f"Cloud: {cloud_name} (edpzc5mm)",
                    f"Fichiers Supabase (ancien): {stats.get('storage_files',0)}",
                    f"Photos Cloudinary: voir console.cloudinary.com",
                    f"Utilisation: 0% de 25 Go",
                    f"",
                    f"LIMITES:",
                    f"Base Supabase: 500 MB gratuit (tu utilises <1%)",
                    f"Photos Cloudinary: 25 Go gratuit = ~160 000 photos",
                
                ]
            else:
                lines = [
                    f"Mode: {stats.get('mode')}",
                    f"Biens total: {stats.get('biens_total', 0)} (actifs: {stats.get('biens_total',0) - stats.get('biens_inactifs',0)}, inactifs: {stats.get('biens_inactifs',0)})",
                    f"Utilisateurs: {stats.get('users_total',0)}",
                    f"Favoris: {stats.get('favoris_total',0)}",
                    f"Notifications: {stats.get('notifications_total',0)}",
                    f"Alertes: {stats.get('alerts_total',0)}",
                    f"OTP codes: {stats.get('otp_codes_total',0)}",
                    f"",
                    f"STOCKAGE SUPABASE (1 Go):",
                    f"Fichiers: {stats.get('storage_files',0)}",
                    f"Taille: {stats.get('storage_size_mb',0)} MB",
                    f"Utilisé: {stats.get('storage_used_percent',0)}% du 1 Go gratuit",
                    f"",
                    f"LIMITES GRATUIT:",
                    f"Base: {stats.get('limits',{}).get('database_free','500 MB')}",
                    f"Storage: {stats.get('limits',{}).get('storage_free','1 GB')}",
                    f"⚠️ Passe à Cloudinary pour 25 Go !",
                ]
            stats_text.value = "\n".join(lines)
            
            # Couleur selon usage
            if stats.get('storage_used_percent',0) > 80:
                stats_text.color = COLORS["danger"]
            elif stats.get('storage_used_percent',0) > 60:
                stats_text.color = "#FF9800"
            else:
                stats_text.color = COLORS["text"]
                
        except Exception as ex:
            stats_text.value = f"Erreur: {ex}"
            stats_text.color = COLORS["danger"]
        
        progress.visible = False
        page.update()
    
    def do_cleanup_orphans(e):
        progress.visible = True
        page.update()
        try:
            count = db.cleanup_orphan_photos()
            snack(page, f"{count} photos orphelines supprimées")
            refresh_stats()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)
        progress.visible = False
        page.update()
    
    def do_cleanup_old(e):
        progress.visible = True
        page.update()
        try:
            result = db.cleanup_old_data(days_notifications=30, days_otps=2)
            snack(page, f"Nettoyé: {result['notifications']} notifs, {result['otps']} OTP")
            refresh_stats()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)
        progress.visible = False
        page.update()
    
    def do_optimize(e):
        progress.visible = True
        page.update()
        try:
            result = db.optimize_storage()
            snack(page, f"Optimisé ! {result['orphan_deleted']} photos + {result['old_data']} vieilles données")
            refresh_stats()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)
        progress.visible = False
        page.update()
    
    def do_check_old_biens(e):
        progress.visible = True
        page.update()
        try:
            result = db.delete_old_inactive_biens(days=90, dry_run=True)
            if result["count"] == 0:
                snack(page, "Aucune vieille annonce inactive à supprimer")
            else:
                # Dialogue confirmation
                def confirm_delete(ev):
                    try:
                        res = db.delete_old_inactive_biens(days=90, dry_run=False)
                        snack(page, f"{res['count']} annonces supprimées")
                        close_dialog(dlg)
                        refresh_stats()
                    except Exception as ex:
                        snack(page, f"Erreur: {ex}", error=True)
                
                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(f"Supprimer {result['count']} annonces ?"),
                    content=ft.Text(f"{result['count']} annonces inactives de plus de 90 jours seront définitivement supprimées avec leurs photos.\n\nContinuer ?"),
                    actions=[
                        ft.TextButton("Annuler", on_click=lambda e: close_dialog(dlg)),
                        ft.TextButton("Supprimer", on_click=confirm_delete, style=ft.ButtonStyle(color=COLORS["danger"])),
                    ]
                )
                def close_dialog(d):
                    d.open = False
                    page.update()
                page.dialog = dlg
                dlg.open = True
                page.update()
        except Exception as ex:
            snack(page, f"Erreur: {ex}", error=True)
        progress.visible = False
        page.update()
    
    refresh_stats()
    
    content = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, controls=[
        ft.Text("Gestion Base de Données", size=22, weight=ft.FontWeight.BOLD),
        ft.Text("Surveille et optimise ton stockage Supabase", size=12, color=COLORS["muted"]),
        progress,
        ft.Container(bgcolor="#FFFFFF", border_radius=12, padding=14, border=ft.border.all(1, "#E0E4E1"), content=stats_text),
        ft.ElevatedButton("Rafraîchir stats", icon=ft.Icons.REFRESH, on_click=refresh_stats, style=ft.ButtonStyle(bgcolor=COLORS["primary"], color="#FFFFFF")),
        ft.Divider(),
        ft.Text("Nettoyage", weight=ft.FontWeight.BOLD, size=16),
        ft.ElevatedButton("Supprimer photos orphelines", icon=ft.Icons.CLEANING_SERVICES, on_click=do_cleanup_orphans, style=ft.ButtonStyle(bgcolor="#FFFFFF", color=COLORS["primary"])),
        ft.ElevatedButton("Supprimer vieilles notifications + OTP (>30j)", icon=ft.Icons.DELETE_SWEEP, on_click=do_cleanup_old, style=ft.ButtonStyle(bgcolor="#FFFFFF", color=COLORS["primary"])),
        ft.ElevatedButton("Optimiser tout (recommandé)", icon=ft.Icons.ROCKET_LAUNCH, on_click=do_optimize, style=ft.ButtonStyle(bgcolor=COLORS["accent"], color="#FFFFFF")),
        ft.Divider(),
        ft.Text("Annonces inactives", weight=ft.FontWeight.BOLD, size=16),
        ft.Text("Supprime les annonces non approuvées ou désactivées de plus de 90 jours", size=11, color=COLORS["muted"]),
        ft.OutlinedButton("Voir & Supprimer vieilles annonces inactives", icon=ft.Icons.DELETE_FOREVER, on_click=do_check_old_biens, style=ft.ButtonStyle(color=COLORS["danger"])),
        ft.Container(height=20),
        ft.Container(bgcolor="#E8F5E9", border_radius=12, padding=12, content=ft.Column(spacing=6, controls=[
            ft.Text("Tu es sur Cloudinary 25 Go", weight=ft.FontWeight.BOLD, size=13, color=COLORS["primary"]),
            ft.Text("• Photos stockées sur Cloudinary (edpzc5mm) - 25 Go = 160 000 photos", size=11),
            ft.Text("• Compression auto: 1280px max, format WebP auto", size=11),
            ft.Text("• Supabase ne stocke plus que le texte (500 Mo = 500 000 annonces)", size=11),
            ft.Text("• Supprime vieilles notifs 1x/mois pour rester clean", size=11),
            ft.Text("• Vérifie usage: console.cloudinary.com > Rapports d'utilisation", size=11),
        ])),
        ft.Container(height=30),
    ])
    
    return ft.View(
        route="/admin/storage",
        bgcolor=COLORS["bg"],
        padding=14,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(title=ft.Text("Gestion Stockage", color="#FFFFFF"), bgcolor=COLORS["primary"], leading=ft.IconButton(ft.Icons.ARROW_BACK, icon_color="#FFFFFF", on_click=lambda e: page.go("/admin"))),
        controls=[content],
    )
