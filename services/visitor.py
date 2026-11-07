"""Etat PAR VISITEUR pour IMMOBILE en version web.

Sur Android il n'y a qu'un utilisateur par processus. En web, UN SEUL programme
Python sert TOUS les visiteurs : session, langue, filtres et brouillons ne
peuvent donc plus etre des variables globales.

Ce module range chaque donnee sur l'objet `page` du visiteur (une `page` par
onglet/connexion), ce qui garantit qu'un visiteur ne voit jamais l'etat d'un autre.

  - SessionFactory.bind(page)  -> objet qui se comporte comme l'ancien `Session`
                                  mais lie a UNE page (utilise par appliquer_web_multi.sh)
  - PageDict(nom, defauts)     -> dict "global" qui pointe en realite vers le dict
                                  de la page courante (filtres de l'accueil, brouillon d'inscription)
  - get_value / set_value      -> petites valeurs par page (langue)

Ce fichier n'importe RIEN de lourd au demarrage (services.auth est charge a la demande).
"""
from __future__ import annotations

import copy
import sys
import threading
from collections.abc import MutableMapping
from typing import Any, Callable, Optional

_STORE_ATTR = "_imm_store"
_USER_ATTR = "_imm_user"
_FALLBACK_STORES: dict = {}          # si la page refuse les attributs (rare)
_FALLBACK_USERS: dict = {}
_SHARED_STORE: dict = {}             # repli quand aucune page n'est trouvee (valeurs cosmetiques seulement)
_LOCK = threading.RLock()


# ------------------------------------------------------------------ page courante
def _looks_like_page(obj: Any) -> bool:
    try:
        return (obj is not None and hasattr(obj, "client_storage")
                and hasattr(obj, "go") and hasattr(obj, "views"))
    except Exception:
        return False


def _page_from(obj: Any) -> Optional[Any]:
    if obj is None:
        return None
    if _looks_like_page(obj):
        return obj
    try:
        p = getattr(obj, "page", None)          # evenement Flet (e.page) ou composant (self.page)
        if _looks_like_page(p):
            return p
        c = getattr(obj, "control", None)       # e.control.page
        p = getattr(c, "page", None) if c is not None else None
        if _looks_like_page(p):
            return p
    except Exception:
        pass
    return None


def current_page(max_depth: int = 80) -> Optional[Any]:
    """Retrouve la page du visiteur en remontant la pile d'appels (variables `page`, `e`, `self`)."""
    try:
        frame = sys._getframe(2)
    except ValueError:
        return None
    depth = 0
    while frame is not None and depth < max_depth:
        try:
            loc = frame.f_locals
            for name in ("page", "e", "self"):
                if name in loc:
                    p = _page_from(loc[name])
                    if p is not None:
                        return p
        except Exception:
            pass
        frame = frame.f_back
        depth += 1
    return None


# ------------------------------------------------------------------- stockage page
def _store(page: Any) -> dict:
    try:
        st = getattr(page, _STORE_ATTR, None)
        if st is None:
            st = {}
            setattr(page, _STORE_ATTR, st)
        return st
    except Exception:
        return _FALLBACK_STORES.setdefault(id(page), {})


def get_value(name: str, default: Any = None) -> Any:
    page = current_page()
    if page is None:
        return _SHARED_STORE.get(name, default)
    return _store(page).get(name, default)


def set_value(page: Any, name: str, value: Any) -> None:
    if page is None:
        _SHARED_STORE[name] = value
    else:
        _store(page)[name] = value


class PageDict(MutableMapping):
    """Se comporte comme un dict global mais lit/ecrit le dict de la page courante."""

    def __init__(self, name: str, defaults: Any):
        self._name = name
        self._defaults = defaults

    def _fresh(self) -> dict:
        d = self._defaults() if callable(self._defaults) else copy.deepcopy(self._defaults)
        return d if isinstance(d, dict) else {}

    def _data(self) -> dict:
        page = current_page()
        st = _SHARED_STORE if page is None else _store(page)
        d = st.get(self._name)
        if d is None:
            d = st[self._name] = self._fresh()
        return d

    def __getitem__(self, k):
        return self._data()[k]

    def __setitem__(self, k, v):
        self._data()[k] = v

    def __delitem__(self, k):
        del self._data()[k]

    def __iter__(self):
        return iter(self._data())

    def __len__(self):
        return len(self._data())

    def __repr__(self):
        return f"PageDict({self._name!r}, {self._data()!r})"


# ---------------------------------------------------------------------- session
def _get_user(page: Any):
    try:
        return getattr(page, _USER_ATTR, None)
    except Exception:
        return _FALLBACK_USERS.get(id(page))


def _set_user(page: Any, user: Any) -> None:
    try:
        setattr(page, _USER_ATTR, user)
    except Exception:
        _FALLBACK_USERS[id(page)] = user


def _call(page: Any, fn: Callable, *args, **kwargs):
    """Execute une methode de l'ancienne classe Session pour CE visiteur.

    Les methodes d'origine lisent/ecrivent `Session.user` (global) : on y place
    l'utilisateur de la page, on appelle, on recupere le resultat, puis on remet
    le global a None. Le verrou garantit qu'un seul visiteur a la fois y touche.
    """
    from services.auth import Session as _S      # import a la demande (charge la base)
    with _LOCK:
        _S.user = _get_user(page)
        try:
            return fn(*args, **kwargs)
        finally:
            _set_user(page, _S.user)
            _S.user = None


class _BoundSession:
    """Meme interface que l'ancien `Session`, mais lie a UNE page."""
    __slots__ = ("_page",)

    def __init__(self, page: Any):
        object.__setattr__(self, "_page", page)

    @property
    def user(self):
        return _get_user(self._page)

    @user.setter
    def user(self, value):
        _set_user(self._page, value)

    def is_logged(self) -> bool:
        return self.user is not None

    def __getattr__(self, name: str):
        from services.auth import Session as _S
        target = getattr(_S, name)               # AttributeError si la methode n'existe pas
        if not callable(target):
            return target
        page = self._page

        def call(*a, **k):
            return _call(page, target, *a, **k)
        return call


class SessionFactory:
    """Remplace `from services.auth import Session` : `Session = SessionFactory.bind(page)`."""

    @staticmethod
    def bind(page: Any) -> _BoundSession:
        return _BoundSession(page)
