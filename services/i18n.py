"""Internationalisation (i18n) de IMMOBILE.

- `translations` regroupe les textes de l'app pour fr / en (l'espagnol existe
  encore dans le dictionnaire mais n'est plus propose : voir LANGUAGES).
- `init_lang(page)` doit etre appele une fois au demarrage : il regarde
  d'abord `page.client_storage` (choix deja fait par l'utilisateur), sinon
  tente de detecter la langue du telephone via `page.locale_configuration`
  (disponible en Flet 0.27+), sinon retombe sur 'fr'.
- `t(key)` renvoie la traduction de la cle dans la langue courante (avec
  repli sur le francais puis sur la cle elle-meme si rien n'est trouve).
"""

from __future__ import annotations

from typing import Optional

import flet as ft
try:
    FT_ICONS = ft.Icons
except:
    FT_ICONS = ft.icons


from services.config import DEFAULT_LANGUAGE, LANGUAGES

# L'app est limitee aux langues declarees dans config.py (FR / EN).
SUPPORTED_LANGS = tuple(LANGUAGES)
DEFAULT_LANG = DEFAULT_LANGUAGE

_state = {"lang": DEFAULT_LANG}

translations = {
    "fr": {
        "app_tagline": "L'immobilier, partout, simplement.",
        # --- Login / Register ---
        "login_title": "Connexion",
        "phone_label": "Telephone",
        "password_label": "Mot de passe",
        "confirm_password_label": "Confirmer le mot de passe",
        "login_button": "Se connecter",
        "no_account": "Pas encore de compte ? Creer un compte",
        "has_account": "J'ai deja un compte",
        "register_title": "Creer un compte",
        "name_label": "Nom complet",
        "email_label": "Email",
        "country_label": "Pays",
        "city_label": "Ville",
        "zone_label": "Zone / Quartier",
        "continue_button": "Continuer",
        "create_account_button": "Creer mon compte",
        "welcome_message": "Bienvenue sur IMMOBILE !",
        "invalid_credentials": "Numero ou mot de passe incorrect.",
        "account_blocked": "Ce compte a ete bloque par l'administrateur.",
        "registration_closed": "Les inscriptions sont temporairement fermees.",
        "name_too_short": "Nom trop court (3 caracteres minimum).",
        "invalid_phone": "Numero de telephone invalide pour ce pays.",
        "password_too_short": "Mot de passe : 6 caracteres minimum.",
        "passwords_mismatch": "Les mots de passe ne correspondent pas.",
        "zone_required": "Indiquez votre zone / quartier.",
        "phone_taken": "Ce numero est deja utilise.",
        # --- CGU ---
        "cgu_title": "Conditions generales d'utilisation",
        "cgu_accept_checkbox": "J'accepte les conditions generales d'utilisation",
        "cgu_must_accept": "Vous devez accepter les CGU pour continuer.",
        "cgu_body": (
            "En utilisant IMMOBILE, vous acceptez de publier des annonces "
            "immobilieres exactes et de respecter les autres utilisateurs. "
            "Toute annonce frauduleuse, trompeuse ou illegale pourra etre "
            "supprimee et votre compte suspendu. Vos donnees personnelles "
            "sont utilisees uniquement pour le fonctionnement de "
            "l'application et ne sont jamais revendues a des tiers. "
            "Les transactions financieres entre utilisateurs se font sous "
            "leur seule responsabilite ; IMMOBILE n'est qu'une plateforme "
            "de mise en relation. Vous devez etre majeur pour creer un "
            "compte. L'application se reserve le droit de moderer, "
            "refuser ou retirer toute annonce ne respectant pas ces regles."
        ),
        # --- Settings ---
        "settings_title": "Parametres",
        "language_label": "Langue / Language",
        # --- Splash ---
        "loading": "Chargement...",
        # --- Home ---
        "search_placeholder": "Rechercher (titre, ville, quartier)",
        "filter_all": "Tous",
        "filter_sale_house": "Vente Maison",
        "filter_sale_land": "Vente Terrain",
        "filter_rent": "Location",
        "all_countries": "Tous les pays",
        "price_min": "Prix min",
        "price_max": "Prix max",
        "negotiable_only": "Prix discutable uniquement",
        "apply_filters": "Appliquer les filtres",
        "no_results": "Aucun bien ne correspond a votre recherche.",
        "price_on_site": "Prix sur place",
        "price_not_specified": "Prix non precise",
        "negotiable_suffix": " (negociable)",
        "details_button": "Details",
        "whatsapp_contact": "Contacter via WhatsApp",
        # --- Nav ---
        "nav_home": "Accueil",
        "nav_favorites": "Favoris",
        "nav_my_listings": "Mes annonces",
        "nav_profile": "Profil",
        "nav_alerts": "Alertes",
        # --- Publish ---
        "publish_title": "Publier un bien",
        "title_label": "Titre de l'annonce",
        "type_label": "Type de bien",
        "category_label": "Categorie",
        "price_label": "Prix",
        "negotiable_checkbox": "Prix discutable",
        "price_on_site_checkbox": "Prix sur place",
        "whatsapp_number_label": "Numero WhatsApp",
        "description_label": "Description",
        "surface_label": "Superficie (m2)",
        "rooms_label": "Chambres",
        "bathrooms_label": "Salles de bain",
        "photos_label": "Photos (1 a 5)",
        "add_photo_url": "Ajouter une photo par URL",
        "publish_button": "Publier l'annonce",
        "publish_success": "Annonce publiee avec succes !",
        "title_required": "Le titre est obligatoire.",
        "zone_required_publish": "La zone / quartier est obligatoire.",
        "whatsapp_required": "Le numero WhatsApp est obligatoire.",
        "photo_required": "Ajoutez au moins 1 photo (max 5).",
        "price_required": "Indiquez un prix ou cochez 'Prix sur place'.",
        "max_photos": "Maximum {n} photos.",
        "upload_failed": "Upload impossible : {err}",
        # --- Alerts ---
        "alerts_title": "Alertes par zone",
        "add_alert_button": "Creer une alerte",
        "no_alerts": "Vous n'avez aucune alerte active.",
        "alert_saved": "Alerte enregistree !",
        "delete_alert": "Supprimer l'alerte",
        # --- Profile ---
        "profile_title": "Mon profil",
        "save_button": "Enregistrer",
        "logout_button": "Se deconnecter",
        "profile_updated": "Profil mis a jour.",
        # --- Notifications / favorites / listings ---
        "notifications_title": "Notifications",
        "no_notifications": "Aucune notification.",
        "favorites_title": "Mes favoris",
        "no_favorites": "Aucun favori pour le moment.",
        "my_listings_title": "Mes annonces",
        "no_listings": "Vous n'avez publie aucune annonce.",
        "listing_deleted": "Annonce supprimee.",
    },
    "en": {
        "app_tagline": "Real estate, everywhere, made simple.",
        "login_title": "Login",
        "phone_label": "Phone",
        "password_label": "Password",
        "confirm_password_label": "Confirm password",
        "login_button": "Sign in",
        "no_account": "No account yet? Create one",
        "has_account": "I already have an account",
        "register_title": "Create an account",
        "name_label": "Full name",
        "email_label": "Email",
        "country_label": "Country",
        "city_label": "City",
        "zone_label": "Zone / Neighborhood",
        "continue_button": "Continue",
        "create_account_button": "Create my account",
        "welcome_message": "Welcome to IMMOBILE!",
        "invalid_credentials": "Incorrect phone number or password.",
        "account_blocked": "This account has been blocked by the administrator.",
        "registration_closed": "Registrations are temporarily closed.",
        "name_too_short": "Name too short (3 characters minimum).",
        "invalid_phone": "Invalid phone number for this country.",
        "password_too_short": "Password: 6 characters minimum.",
        "passwords_mismatch": "Passwords do not match.",
        "zone_required": "Please enter your zone / neighborhood.",
        "phone_taken": "This phone number is already in use.",
        "cgu_title": "Terms of Service",
        "cgu_accept_checkbox": "I accept the Terms of Service",
        "cgu_must_accept": "You must accept the Terms of Service to continue.",
        "cgu_body": (
            "By using IMMOBILE, you agree to post accurate real estate "
            "listings and to respect other users. Any fraudulent, "
            "misleading or illegal listing may be removed and your "
            "account suspended. Your personal data is used only to "
            "operate the application and is never sold to third "
            "parties. Financial transactions between users are made "
            "under their sole responsibility; IMMOBILE is only a "
            "matchmaking platform. You must be of legal age to create "
            "an account. The application reserves the right to "
            "moderate, refuse or remove any listing that does not "
            "follow these rules."
        ),
        "settings_title": "Settings",
        "language_label": "Language / Langue",
        "loading": "Loading...",
        "search_placeholder": "Search (title, city, neighborhood)",
        "filter_all": "All",
        "filter_sale_house": "House for sale",
        "filter_sale_land": "Land for sale",
        "filter_rent": "Rent",
        "all_countries": "All countries",
        "price_min": "Min price",
        "price_max": "Max price",
        "negotiable_only": "Negotiable price only",
        "apply_filters": "Apply filters",
        "no_results": "No listing matches your search.",
        "price_on_site": "Price on site",
        "price_not_specified": "Price not specified",
        "negotiable_suffix": " (negotiable)",
        "details_button": "Details",
        "whatsapp_contact": "Contact via WhatsApp",
        "nav_home": "Home",
        "nav_favorites": "Favorites",
        "nav_my_listings": "My listings",
        "nav_profile": "Profile",
        "nav_alerts": "Alerts",
        "publish_title": "Publish a listing",
        "title_label": "Listing title",
        "type_label": "Property type",
        "category_label": "Category",
        "price_label": "Price",
        "negotiable_checkbox": "Negotiable price",
        "price_on_site_checkbox": "Price on site",
        "whatsapp_number_label": "WhatsApp number",
        "description_label": "Description",
        "surface_label": "Surface (m2)",
        "rooms_label": "Bedrooms",
        "bathrooms_label": "Bathrooms",
        "photos_label": "Photos (1 to 5)",
        "add_photo_url": "Add a photo by URL",
        "publish_button": "Publish listing",
        "publish_success": "Listing published successfully!",
        "title_required": "Title is required.",
        "zone_required_publish": "The zone / neighborhood is required.",
        "whatsapp_required": "WhatsApp number is required.",
        "photo_required": "Add at least 1 photo (max 5).",
        "price_required": "Enter a price or check 'Price on site'.",
        "max_photos": "Maximum {n} photos.",
        "upload_failed": "Upload failed: {err}",
        "alerts_title": "Zone alerts",
        "add_alert_button": "Create an alert",
        "no_alerts": "You have no active alerts.",
        "alert_saved": "Alert saved!",
        "delete_alert": "Delete alert",
        "profile_title": "My profile",
        "save_button": "Save",
        "logout_button": "Sign out",
        "profile_updated": "Profile updated.",
        "notifications_title": "Notifications",
        "no_notifications": "No notifications.",
        "favorites_title": "My favorites",
        "no_favorites": "No favorites yet.",
        "my_listings_title": "My listings",
        "no_listings": "You haven't published any listings.",
        "listing_deleted": "Listing deleted.",
    },
    "es": {
        "app_tagline": "Bienes raices, en todas partes, de forma simple.",
        "login_title": "Iniciar sesion",
        "phone_label": "Telefono",
        "password_label": "Contrasena",
        "confirm_password_label": "Confirmar contrasena",
        "login_button": "Iniciar sesion",
        "no_account": "No tienes cuenta? Crea una",
        "has_account": "Ya tengo una cuenta",
        "register_title": "Crear una cuenta",
        "name_label": "Nombre completo",
        "email_label": "Correo electronico",
        "country_label": "Pais",
        "city_label": "Ciudad",
        "zone_label": "Zona / Barrio",
        "continue_button": "Continuar",
        "create_account_button": "Crear mi cuenta",
        "welcome_message": "Bienvenido a IMMOBILE!",
        "invalid_credentials": "Numero o contrasena incorrectos.",
        "account_blocked": "Esta cuenta ha sido bloqueada por el administrador.",
        "registration_closed": "Los registros estan temporalmente cerrados.",
        "name_too_short": "Nombre demasiado corto (minimo 3 caracteres).",
        "invalid_phone": "Numero de telefono invalido para este pais.",
        "password_too_short": "Contrasena: minimo 6 caracteres.",
        "passwords_mismatch": "Las contrasenas no coinciden.",
        "zone_required": "Indique su zona / barrio.",
        "phone_taken": "Este numero ya esta en uso.",
        "cgu_title": "Terminos y condiciones",
        "cgu_accept_checkbox": "Acepto los terminos y condiciones",
        "cgu_must_accept": "Debe aceptar los terminos para continuar.",
        "cgu_body": (
            "Al usar IMMOBILE, aceptas publicar anuncios inmobiliarios "
            "precisos y respetar a los demas usuarios. Cualquier anuncio "
            "fraudulento, enganoso o ilegal podra ser eliminado y tu "
            "cuenta suspendida. Tus datos personales se usan solo para "
            "el funcionamiento de la aplicacion y nunca se venden a "
            "terceros. Las transacciones financieras entre usuarios se "
            "realizan bajo su unica responsabilidad; IMMOBILE es solo "
            "una plataforma de contacto. Debes ser mayor de edad para "
            "crear una cuenta. La aplicacion se reserva el derecho de "
            "moderar, rechazar o retirar cualquier anuncio que no "
            "respete estas reglas."
        ),
        "settings_title": "Configuracion",
        "language_label": "Idioma / Language",
        "loading": "Cargando...",
        "search_placeholder": "Buscar (titulo, ciudad, barrio)",
        "filter_all": "Todos",
        "filter_sale_house": "Venta casa",
        "filter_sale_land": "Venta terreno",
        "filter_rent": "Alquiler",
        "all_countries": "Todos los paises",
        "price_min": "Precio min",
        "price_max": "Precio max",
        "negotiable_only": "Solo precio negociable",
        "apply_filters": "Aplicar filtros",
        "no_results": "Ningun inmueble coincide con su busqueda.",
        "price_on_site": "Precio en el lugar",
        "price_not_specified": "Precio no especificado",
        "negotiable_suffix": " (negociable)",
        "details_button": "Detalles",
        "whatsapp_contact": "Contactar por WhatsApp",
        "nav_home": "Inicio",
        "nav_favorites": "Favoritos",
        "nav_my_listings": "Mis anuncios",
        "nav_profile": "Perfil",
        "nav_alerts": "Alertas",
        "publish_title": "Publicar un inmueble",
        "title_label": "Titulo del anuncio",
        "type_label": "Tipo de inmueble",
        "category_label": "Categoria",
        "price_label": "Precio",
        "negotiable_checkbox": "Precio negociable",
        "price_on_site_checkbox": "Precio en el lugar",
        "whatsapp_number_label": "Numero de WhatsApp",
        "description_label": "Descripcion",
        "surface_label": "Superficie (m2)",
        "rooms_label": "Habitaciones",
        "bathrooms_label": "Banos",
        "photos_label": "Fotos (1 a 5)",
        "add_photo_url": "Anadir una foto por URL",
        "publish_button": "Publicar anuncio",
        "publish_success": "Anuncio publicado con exito!",
        "title_required": "El titulo es obligatorio.",
        "zone_required_publish": "La zona / barrio es obligatorio.",
        "whatsapp_required": "El numero de WhatsApp es obligatorio.",
        "photo_required": "Anada al menos 1 foto (max 5).",
        "price_required": "Indique un precio o marque 'Precio en el lugar'.",
        "max_photos": "Maximo {n} fotos.",
        "upload_failed": "Error al subir: {err}",
        "alerts_title": "Alertas por zona",
        "add_alert_button": "Crear una alerta",
        "no_alerts": "No tiene alertas activas.",
        "alert_saved": "Alerta guardada!",
        "delete_alert": "Eliminar alerta",
        "profile_title": "Mi perfil",
        "save_button": "Guardar",
        "logout_button": "Cerrar sesion",
        "profile_updated": "Perfil actualizado.",
        "notifications_title": "Notificaciones",
        "no_notifications": "Sin notificaciones.",
        "favorites_title": "Mis favoritos",
        "no_favorites": "Sin favoritos por el momento.",
        "my_listings_title": "Mis anuncios",
        "no_listings": "No ha publicado ningun anuncio.",
        "listing_deleted": "Anuncio eliminado.",
    },
}


# Fusion des textes supplementaires (services/translations.py).
from services.translations import EXTRA as _EXTRA  # noqa: E402

for _lang, _texts in _EXTRA.items():
    translations.setdefault(_lang, {}).update(_texts)


def _detect_device_lang(page: ft.Page) -> str:
    """Best-effort detection of the phone's language. Falls back to 'fr'."""
    try:
        cfg = getattr(page, "locale_configuration", None)
        if cfg and getattr(cfg, "supported_locales", None):
            candidate = cfg.supported_locales[0]
            code = getattr(candidate, "language_code", None)
            if code in SUPPORTED_LANGS:
                return code
    except Exception:
        pass
    try:
        pl = getattr(page, "platform_brightness", None)  # noqa: F841 (best effort only)
    except Exception:
        pass
    return DEFAULT_LANG


def init_lang(page: ft.Page) -> str:
    """Load the language once at startup: storage first, then device, then fr."""
    try:
        stored = page.client_storage.get("lang")
    except Exception:
        stored = None
    if stored in SUPPORTED_LANGS:
        _state["lang"] = stored
        return stored
    lang = _detect_device_lang(page)
    _state["lang"] = lang
    try:
        page.client_storage.set("lang", lang)
    except Exception:
        pass
    return lang


def set_lang(page: ft.Page, lang: str) -> None:
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    _state["lang"] = lang
    try:
        page.client_storage.set("lang", lang)
    except Exception:
        pass


def get_lang() -> str:
    return _state["lang"]


def t(key: str, **kwargs) -> str:
    lang = _state["lang"]
    text = translations.get(lang, {}).get(key)
    if text is None:
        text = translations[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
