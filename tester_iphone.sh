#!/usr/bin/env bash
# =============================================================================
#  tester_iphone.sh  -  Teste IMMOBILE sur iPhone (mode web, depuis Linux)
#
#  1) iPhone et ordinateur sur le MEME Wi-Fi
#  2) venv active, puis :   bash tester_iphone.sh
#  3) Dans Safari (iPhone), ouvrez l'adresse affichee
#  4) Partager > "Sur l'ecran d'accueil" : icone plein ecran, comme une appli
#
#  Variable : PORT=8560 bash tester_iphone.sh   (autre port)
#  Note : l'application tourne sur l'ordinateur, l'iPhone n'est que l'ecran.
#         Ce n'est donc PAS un test de vitesse de l'appli native.
# =============================================================================
set -euo pipefail

if [ -t 1 ]; then C1=$'\033[1;36m'; C2=$'\033[1;32m'; C3=$'\033[1;33m'; C4=$'\033[1;31m'; C0=$'\033[0m'; else C1=; C2=; C3=; C4=; C0=; fi
warn() { printf '%s !  %s%s\n' "$C3" "$*" "$C0"; }
die()  { printf '%s ERREUR : %s%s\n' "$C4" "$*" "$C0" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
[ -f main.py ] || die "Lancez ce script depuis la racine du projet (main.py)."
PORT="${PORT:-8550}"

FLET="$(command -v flet || true)"
[ -n "$FLET" ] || { [ -x "$ROOT/venv/bin/flet" ] && FLET="$ROOT/venv/bin/flet"; }
[ -n "$FLET" ] || die "commande 'flet' introuvable. Activez votre venv :  source venv/bin/activate"

lan_ip() {
  local ip=""
  if command -v ip >/dev/null 2>&1; then
    ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' || true)
  fi
  [ -n "$ip" ] || ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
  printf '%s' "$ip"
}
IP="$(lan_ip)"
[ -n "$IP" ] || die "Adresse IP du reseau local introuvable : etes-vous connecte au Wi-Fi ?"
case "$IP" in 127.*) die "Seule l'adresse locale $IP est disponible : connectez-vous a un reseau Wi-Fi." ;; esac

port_libre() {
  python3 - "$1" <<'PY'
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", int(sys.argv[1])))
except OSError:
    sys.exit(1)
PY
}
port_libre "$PORT" || die "Le port $PORT est deja utilise. Essayez :  PORT=8560 bash tester_iphone.sh"
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
  warn "Pare-feu actif : si l'iPhone n'arrive pas a se connecter, lancez :  sudo ufw allow $PORT/tcp"
fi

echo
printf '%s==> Sur votre iPhone (meme Wi-Fi), ouvrez Safari a l'\''adresse :%s\n\n' "$C1" "$C0"
printf '        %shttp://%s:%s%s\n\n' "$C2" "$IP" "$PORT" "$C0"
echo "    Astuce : Partager > \"Sur l'ecran d'accueil\" pour l'avoir en plein ecran."
echo "    (Ctrl+C pour arreter. Au premier lancement, flet peut installer 'flet-web'.)"
echo

exec "$FLET" run --web --host "*" --port "$PORT" main.py
