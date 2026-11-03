#!/usr/bin/env bash
# =============================================================================
#  build_apk.sh  -  Construit l'APK IMMOBILE depuis une COPIE PROPRE du projet
#
#  Pourquoi : "flet build" empaquette TOUT le dossier (venv/, source/, .git/ ...),
#  ce qui ajoutait ~100 Mo inutiles a l'APK.
#
#  Usage (depuis la racine du projet, venv active) :
#     bash build_apk.sh                     # APK par architecture dans ./apk
#     ARCH="arm64-v8a" bash build_apk.sh    # une seule architecture (plus rapide)
#     bash build_apk.sh --propre            # repart de zero (vide le cache de build)
#     COMPILE=1 bash build_apk.sh           # precompile le code (.pyc) : demarrage plus rapide
# =============================================================================
set -euo pipefail

CLEAN=0
for arg in "$@"; do
  case "$arg" in
    --propre) CLEAN=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Option inconnue : $arg"; exit 2 ;;
  esac
done

if [ -t 1 ]; then C1=$'\033[1;36m'; C2=$'\033[1;32m'; C3=$'\033[1;33m'; C4=$'\033[1;31m'; C0=$'\033[0m'; else C1=; C2=; C3=; C4=; C0=; fi
say()  { printf '\n%s==> %s%s\n' "$C1" "$*" "$C0"; }
ok()   { printf '%s OK %s%s\n' "$C2" "$*" "$C0"; }
warn() { printf '%s !  %s%s\n' "$C3" "$*" "$C0"; }
die()  { printf '%s ERREUR : %s%s\n' "$C4" "$*" "$C0" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
[ -f main.py ] && [ -f pyproject.toml ] || die "Lancez ce script depuis la racine du projet (main.py + pyproject.toml)."

WANT="0.28.3"

# ------------------------------------------------------------- 1. controles
say "1/4  Controles"
grep -q "flet==$WANT" pyproject.toml \
  || die "pyproject.toml doit contenir \"flet==$WANT\" (sans version, l'APK embarque un Flet incompatible = ecran blanc)."
grep -q "supabase==" pyproject.toml \
  || warn "supabase n'est pas fige dans pyproject.toml (risque d'API differente sur le telephone)."

FLET="$(command -v flet || true)"
[ -n "$FLET" ] || { [ -x "$ROOT/venv/bin/flet" ] && FLET="$ROOT/venv/bin/flet"; }
[ -n "$FLET" ] || die "commande 'flet' introuvable. Activez votre venv :  source venv/bin/activate"
GOT="$("$FLET" --version 2>/dev/null | grep -o -E '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
if [ -z "$GOT" ]; then
  warn "version du CLI flet illisible, je continue."
elif [ "$GOT" != "$WANT" ]; then
  die "le CLI flet est en $GOT mais le code est prevu pour $WANT. Corrigez :  pip install \"flet==$WANT\" \"flet-cli==$WANT\" \"flet-desktop==$WANT\""
fi
ok "CLI flet $GOT  (dependances figees a $WANT dans pyproject.toml)"

# ------------------------------------------------- 2. copie propre du projet
say "2/4  Copie propre du projet (sans venv, source, .git, photos de test...)"
STAGE="${IMMOBILE_STAGE:-$HOME/.cache/immobile_build}"
mkdir -p "$STAGE"
[ "$CLEAN" = 1 ] && rm -rf "$STAGE" && mkdir -p "$STAGE"
# on garde seulement "build" (cache de compilation) d'une fois sur l'autre
find "$STAGE" -mindepth 1 -maxdepth 1 ! -name build -exec rm -rf {} +
tar -C "$ROOT" \
  --exclude='./venv' --exclude='./.venv' --exclude='./source' \
  --exclude='./.git' --exclude='./.github' --exclude='./build' --exclude='./apk' \
  --exclude='./uploads' --exclude='./assets/uploads' --exclude='./local_db.json' \
  --exclude='./main_mobile.py' --exclude='./migrate_to_supabase.py' --exclude='./reset_admin.py' \
  --exclude='./*.sql' --exclude='./*.sh' --exclude='./MD5SUMS.txt' --exclude='./build.log' \
  --exclude='./.sauvegarde*' --exclude='__pycache__' \
  -cf - . | tar -C "$STAGE" -xf -
N=$(find "$STAGE" -path "$STAGE/build" -prune -o -type f -print | wc -l)
S=$(du -sk --exclude=build "$STAGE" | cut -f1)
ok "$N fichiers, $((S / 1024)) Mo a empaqueter (avant : plus de 12 000 fichiers et ~240 Mo)"
[ "$N" -lt 400 ] || warn "$N fichiers : c'est beaucoup, verifiez le contenu de $STAGE"
[ -f "$STAGE/.env" ] || warn ".env absent : l'application demarrera en mode LOCAL (sans Supabase)."

# --------------------------------------------------------------- 3. build
say "3/4  Construction de l'APK (premiere fois : plusieurs minutes)"
ARGS=(build apk --project immobile --split-per-abi --verbose)
[ -n "${ARCH:-}" ] && ARGS+=(--arch $ARCH)
[ "${COMPILE:-0}" = 1 ] && ARGS+=(--compile-app --compile-packages)
( cd "$STAGE" && "$FLET" "${ARGS[@]}" ) 2>&1 | tee "$ROOT/build.log" || die "Le build a echoue. Journal complet : $ROOT/build.log"

# --------------------------------------------------------------- 4. resultat
say "4/4  Recuperation des APK"
rm -rf "$ROOT/apk" && mkdir -p "$ROOT/apk"
mapfile -t APKS < <(find "$STAGE/build" -name '*.apk' -type f 2>/dev/null | sort)
[ "${#APKS[@]}" -gt 0 ] || die "Aucun APK trouve. Regardez $ROOT/build.log"
for a in "${APKS[@]}"; do cp "$a" "$ROOT/apk/"; done
echo
for a in "$ROOT"/apk/*.apk; do
  sz=$(du -m "$a" | cut -f1)
  printf '   %-45s %4s Mo\n' "$(basename "$a")" "$sz"
  [ "$sz" -lt 100 ] || warn "$(basename "$a") depasse 100 Mo : verifiez le contenu de $STAGE"
done
echo
ok "APK dans $ROOT/apk"
echo "    Telephone recent (la plupart) : installez celui qui contient 'arm64-v8a'."
echo "    Si l'ecran reste vide :  adb logcat | grep -i -E 'python|flet|IMMOBILE'"
