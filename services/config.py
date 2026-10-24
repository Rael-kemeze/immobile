"""Configuration centrale de l'application IMMOBILE."""

APP_CONFIG = {
    "APP_NAME": "IMMOBILE",
    "ADMIN_PHONE": "+237693376705",
    "ADMIN_PASSWORD": "admin123",
    # Le compte admin est TOUJOURS cree s'il manque, et toujours remis en
    # SUPER_ADMIN / debloque. Le MOT DE PASSE n'est remis a ADMIN_PASSWORD
    # a chaque demarrage que si ce reglage est True. Laissez False : sinon
    # le mot de passe change depuis l'app serait ecrase au lancement suivant.
    # (Mot de passe perdu ? lancez `python reset_admin.py`.)
    "FORCE_ADMIN_ON_START": False,
    "APP_VERSION": "1.0.0",
    "MIN_PASSWORD_LENGTH": 6,
    "ADMIN_MIN_PASSWORD_LENGTH": 8,
    "MAINTENANCE_MODE": False,
    "INSCRIPTION_OUVERTE": True,
    "DEFAULT_COUNTRY_CODE": "CM",
    # Pas de validation : toute annonce publiee est APPROUVE directement.
    "VALIDATION_OBLIGATOIRE": False,
    "DEVISE": "FCFA",  # devise de secours si le pays est inconnu
    "MAX_PHOTOS": 5,
}

# --------------------------------------------------------------------- langues
LANGUAGES = ["fr", "en"]
DEFAULT_LANGUAGE = "fr"

# ----------------------------------------------------------------- pays/villes
# Cle = code pays ISO. La derniere entree "Autre" ouvre un champ de saisie
# libre : on n'est donc jamais limite a la liste.
OTHER_CITY = "Autre"

COUNTRY_CITIES = {
    # --- Afrique centrale
    "CM": ["Bafoussam", "Douala", "Yaounde", "Bamenda", "Dschang", "Buea", "Garoua", "Maroua", "Bertoua", "Kribi", OTHER_CITY],
    "GA": ["Libreville", "Port-Gentil", "Franceville", "Oyem", OTHER_CITY],
    "CG": ["Brazzaville", "Pointe-Noire", "Dolisie", OTHER_CITY],
    "CD": ["Kinshasa", "Lubumbashi", "Goma", "Kisangani", "Mbuji-Mayi", OTHER_CITY],
    "TD": ["N'Djamena", "Moundou", "Sarh", OTHER_CITY],
    # --- Afrique de l'Ouest
    "CI": ["Abidjan", "Yamoussoukro", "Bouake", "San-Pedro", "Daloa", OTHER_CITY],
    "SN": ["Dakar", "Thies", "Saint-Louis", "Touba", "Mbour", OTHER_CITY],
    "ML": ["Bamako", "Sikasso", "Segou", "Kayes", OTHER_CITY],
    "BF": ["Ouagadougou", "Bobo-Dioulasso", "Koudougou", OTHER_CITY],
    "TG": ["Lome", "Kara", "Sokode", "Atakpame", OTHER_CITY],
    "BJ": ["Cotonou", "Porto-Novo", "Parakou", "Abomey-Calavi", OTHER_CITY],
    "NE": ["Niamey", "Zinder", "Maradi", "Agadez", OTHER_CITY],
    "GN": ["Conakry", "Kankan", "Labe", "Nzerekore", OTHER_CITY],
    "NG": ["Lagos", "Abuja", "Port Harcourt", "Ibadan", "Kano", "Enugu", OTHER_CITY],
    "GH": ["Accra", "Kumasi", "Takoradi", "Tamale", "Cape Coast", OTHER_CITY],
    # --- Afrique de l'Est / australe
    "KE": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", OTHER_CITY],
    "UG": ["Kampala", "Entebbe", "Jinja", "Gulu", OTHER_CITY],
    "TZ": ["Dar es Salaam", "Dodoma", "Arusha", "Mwanza", "Zanzibar", OTHER_CITY],
    "RW": ["Kigali", "Huye", "Musanze", "Rubavu", OTHER_CITY],
    "ZA": ["Johannesburg", "Cape Town", "Durban", "Pretoria", OTHER_CITY],
    "MG": ["Antananarivo", "Toamasina", "Mahajanga", "Fianarantsoa", OTHER_CITY],
    # --- Afrique du Nord
    "MA": ["Casablanca", "Rabat", "Marrakech", "Tanger", "Fes", OTHER_CITY],
    "DZ": ["Alger", "Oran", "Constantine", "Annaba", OTHER_CITY],
    "TN": ["Tunis", "Sfax", "Sousse", "Bizerte", OTHER_CITY],
    # --- Diaspora
    "FR": ["Paris", "Lyon", "Marseille", "Lille", "Bordeaux", OTHER_CITY],
}

# Devise affichee selon le pays de l'annonce.
CURRENCIES = {
    "CM": "FCFA", "GA": "FCFA", "CG": "FCFA", "TD": "FCFA",
    "CI": "FCFA", "SN": "FCFA", "ML": "FCFA", "BF": "FCFA",
    "TG": "FCFA", "BJ": "FCFA", "NE": "FCFA",
    "CD": "CDF", "GN": "GNF", "MG": "MGA",
    "NG": "NGN", "GH": "GHS", "KE": "KES", "UG": "UGX",
    "TZ": "TZS", "RW": "RWF", "ZA": "ZAR",
    "MA": "MAD", "DZ": "DZD", "TN": "TND",
    "FR": "EUR",
}


def get_currency(country_code):
    return CURRENCIES.get(country_code) or APP_CONFIG["DEVISE"]


def get_cities(country_code):
    return COUNTRY_CITIES.get(country_code) or [OTHER_CITY]


# --------------------------------------------------------------------- biens
TRANSACTIONS = ["VENTE", "LOCATION"]  # a vendre / a louer

CAT_MAISON = "MAISON"
CAT_STUDIO = "STUDIO"
CAT_CHAMBRE = "CHAMBRE"
CAT_TERRAIN = "TERRAIN"
CATEGORIES = [CAT_MAISON, CAT_STUDIO, CAT_CHAMBRE, CAT_TERRAIN]

# type_bien = TRANSACTION + "_" + CATEGORIE  (ex. LOCATION_STUDIO)
TYPES_BIEN = [f"{tr}_{cat}" for tr in TRANSACTIONS for cat in CATEGORIES]

STATUS_EN_ATTENTE = "EN_ATTENTE"
STATUS_APPROUVE = "APPROUVE"
STATUS_REJETE = "REJETE"

ROLE_USER = "USER"
ROLE_SUPER_ADMIN = "SUPER_ADMIN"

# Palette de couleurs (theme sobre : vert / or / rouge)
COLORS = {
    "primary": "#0F6B3F",
    "primary_dark": "#08492A",
    "accent": "#F2A900",
    "danger": "#C1272D",
    "bg": "#F6F7F5",
    "card": "#FFFFFF",
    "text": "#12211A",
    "muted": "#6B7A72",
}


def build_type_bien(transaction: str, categorie: str) -> str:
    return f"{transaction}_{categorie}"


def transaction_from_type(type_bien: str) -> str:
    return "VENTE" if type_bien.startswith("VENTE") else "LOCATION"


def categorie_from_type(type_bien: str) -> str:
    cat = type_bien.partition("_")[2]
    return cat if cat in CATEGORIES else CAT_MAISON
