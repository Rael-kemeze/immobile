#!/usr/bin/env python3
"""Patch IMMOBILE -> version web multi-visiteurs (tout-ou-rien, idempotent).

Usage : patch_web_multi.py <racine_du_projet>
Sortie : 0 = modifie, 3 = deja applique, 1 = echec (RIEN n'est ecrit).

Ce qu'il fait
  1. Session : chaque `from services.auth import Session` devient un alias, et chaque
     fonction qui utilise `Session` recoit en premiere ligne
         Session = _SessionClass.bind(page)
     => le reste du code (Session.user, Session.is_admin()...) ne change pas, mais
        la session est desormais propre a chaque visiteur.
  2. i18n.py        : la langue devient propre a chaque visiteur.
  3. home_view.py   : STATE (filtres de l'accueil) propre a chaque visiteur.
  4. auth_view.py   : REGISTER_DRAFT (brouillon d'inscription) propre a chaque visiteur.
  5. widgets.py     : noms de fichiers envoyes uniques + nettoyage + chemin securise.
"""
import ast
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
SKIP_DIRS = {"venv", ".venv", "build", "source", ".git", ".github", "node_modules",
             "__pycache__", "apk", "uploads", "demo_data", "deploy_demo", "deploy_web"}
SKIP_FILES = {os.path.join("services", "auth.py"), os.path.join("services", "visitor.py"),
              os.path.join("services", "demo.py")}
IMPORT_RE = re.compile(r"^from\s+services\.auth\s+import\s+Session\s*$")
NEW_IMPORT = "from services.visitor import SessionFactory as _SessionClass"

errors: list = []
new_files: dict = {}     # rel -> (texte, crlf)


def read(rel):
    raw = open(os.path.join(ROOT, rel), encoding="utf-8", newline="").read()
    return ("\r\n" in raw), raw.replace("\r\n", "\n")


def err(rel, msg):
    errors.append(f" - {rel} : {msg}")


# ------------------------------------------------------------ 1. Session par page
LAZY_RE = re.compile(r"^class _LazySession:.*?^Session = _LazySession\(\)[ \t]*\n", re.S | re.M)
notes: list = []


def patch_session(rel, text):
    had_lazy = False
    if LAZY_RE.search(text):        # proxy cree par appliquer_demarrage.sh (main.py)
        text = LAZY_RE.sub(NEW_IMPORT + "\n", text, count=1)
        had_lazy = True
    lines = text.split("\n")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        err(rel, f"syntaxe invalide avant patch ({exc})")
        return None

    # a) import
    imp_nodes = [n for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module == "services.auth"
                 and any(a.name == "Session" for a in n.names)]
    if not imp_nodes and not had_lazy:
        return None
    for n in imp_nodes:
        line = lines[n.lineno - 1]
        if n.col_offset != 0 or not IMPORT_RE.match(line.strip()) or n.lineno != n.end_lineno:
            err(rel, f"import de Session inattendu (ligne {n.lineno}) : {line.strip()!r}")
            return None

    # b) references a Session (hors import)
    refs = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "Session"]

    # c) fonctions "de premier niveau" : def au niveau module, ou methode d'une classe de niveau module
    outer = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            outer.append(node)
        elif isinstance(node, ast.ClassDef):
            outer.extend(n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))

    def inside(fn, ref):
        return fn.lineno <= ref.lineno <= fn.end_lineno

    inserts = []
    covered = set()
    for fn in outer:
        used = [r for r in refs if inside(fn, r)]
        if not used:
            continue
        covered.update(id(r) for r in used)
        argnames = [a.arg for a in (fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs)]
        if "page" in argnames:
            pexpr = "page"
        elif argnames and argnames[0] == "self":
            pexpr = "self.page"
        else:
            pexpr = None        # pas de page : on la retrouve a l'execution (SessionFactory.bind_current)
            notes.append(f"  note    {rel} : '{fn.name}' n'a pas de parametre page -> page retrouvee automatiquement")
        body = fn.body
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant)
                and isinstance(first.value.value, str)):
            if len(body) < 2:
                continue
            first = body[1]
        if first.lineno == fn.lineno:
            err(rel, f"fonction '{fn.name}' ecrite sur une seule ligne (ligne {fn.lineno})")
            continue
        inserts.append((first.lineno, first.col_offset, pexpr))

    leftover = [r for r in refs if id(r) not in covered]
    for r in leftover:
        err(rel, f"Session utilise hors d'une fonction (ligne {r.lineno})")
    if errors:
        return None

    # d) ecriture (de bas en haut pour garder les numeros de ligne valides)
    for lineno, col, pexpr in sorted(set(inserts), key=lambda x: (x[0], x[1]), reverse=True):
        call = "bind_current()" if pexpr is None else f"bind({pexpr})"
        lines.insert(lineno - 1, " " * col + f"Session = _SessionClass.{call}")
    for n in imp_nodes:
        lines[n.lineno - 1] = NEW_IMPORT
    out = "\n".join(lines)
    try:
        ast.parse(out)
    except SyntaxError as exc:
        err(rel, f"syntaxe invalide apres patch ({exc})")
        return None
    return out


# ------------------------------------------------------------------- 2. i18n
def patch_i18n(rel, text):
    if "_visitor" in text:
        return text, "deja"
    out = text
    # import apres la definition de _state
    m = re.search(r'^_state = \{"lang": DEFAULT_LANG\}[ \t]*$', out, re.M)
    if not m:
        err(rel, "ligne '_state = {\"lang\": DEFAULT_LANG}' introuvable")
        return None, None
    out = out[:m.end()] + "\nfrom services import visitor as _visitor  # noqa: E402" + out[m.end():]
    # ecritures (init_lang x2, set_lang x1)
    rx = re.compile(r'^([ \t]*)_state\["lang"\] = (\w+)[ \t]*$', re.M)
    n = len(rx.findall(out))
    if n != 3:
        err(rel, f"{n} ecriture(s) de _state['lang'] au lieu de 3")
        return None, None
    out = rx.sub(lambda mm: f'{mm.group(1)}_state["lang"] = {mm.group(2)}\n'
                            f'{mm.group(1)}_visitor.set_value(page, "lang", {mm.group(2)})', out)
    # lectures (get_lang, t)
    for pat, rep, cnt in ((r'^([ \t]*)return _state\["lang"\][ \t]*$',
                           r'\1return _visitor.get_value("lang", _state["lang"])', 1),
                          (r'^([ \t]*)lang = _state\["lang"\][ \t]*$',
                           r'\1lang = _visitor.get_value("lang", _state["lang"])', 1)):
        rx2 = re.compile(pat, re.M)
        k = len(rx2.findall(out))
        if k < cnt:
            err(rel, f"lecture de _state['lang'] introuvable ({pat})")
            return None, None
        out = rx2.sub(rep, out)
    return out, "ok"


# --------------------------------------------------------------- 3. home_view
def patch_home(rel, text):
    if "_STATE_DEFAULT" in text:
        return text, "deja"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        err(rel, f"syntaxe invalide ({exc})")
        return None, None
    node = next((n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "STATE"), None)
    if node is None:
        err(rel, "definition de STATE introuvable")
        return None, None
    lines = text.split("\n")
    first = lines[node.lineno - 1]
    if not re.match(r"^STATE\s*=\s*\{", first):
        err(rel, f"STATE inattendu : {first!r}")
        return None, None
    lines[node.lineno - 1] = re.sub(r"^STATE\s*=", "_STATE_DEFAULT =", first, count=1)
    lines.insert(node.end_lineno,
                 "from services import visitor as _visitor  # noqa: E402\n"
                 'STATE = _visitor.PageDict("home_state", _STATE_DEFAULT)  # un dict par visiteur')
    return "\n".join(lines), "ok"


# --------------------------------------------------------------- 4. auth_view
def patch_auth_view(rel, text):
    if "PageDict" in text:
        return text, "deja"
    rx = re.compile(r"^REGISTER_DRAFT\s*:\s*dict\s*=\s*\{\}[ \t]*$", re.M)
    if len(rx.findall(text)) != 1:
        err(rel, "ligne 'REGISTER_DRAFT: dict = {}' introuvable")
        return None, None
    out = rx.sub("from services import visitor as _visitor  # noqa: E402\n"
                 'REGISTER_DRAFT = _visitor.PageDict("register_draft", dict)  # un brouillon par visiteur', text)
    return out, "ok"


# ---------------------------------------------------------------- 5. widgets
HELPER = '''def _unique_name(name) -> str:
    """Nom de fichier unique pour un envoi web (deux visiteurs peuvent envoyer 'photo.jpg')."""
    import uuid
    base = os.path.basename(str(name or "photo")).replace(" ", "_")
    return f"{uuid.uuid4().hex[:10]}_{base}"
'''


def patch_widgets(rel, text):
    if "_unique_name" in text:
        return text, "deja"
    out = text
    rx_up = re.compile(r"ft\.FilePickerUploadFile\(\s*f\.name\s*,\s*upload_url\s*=\s*"
                       r"self\.page\.get_upload_url\(\s*f\.name\s*,\s*600\s*\)\s*\)\s+for f in web", re.S)
    if len(rx_up.findall(out)) != 1:
        err(rel, "creation de FilePickerUploadFile introuvable (ImagePicker)")
        return None, None
    out = rx_up.sub("ft.FilePickerUploadFile(_n, upload_url=self.page.get_upload_url(_n, 600)) "
                    "for f in web for _n in [_unique_name(f.name)]", out)
    rx_dl = re.compile(r"^([ \t]*)self\._deliver\(\[os\.path\.join\(str\(WEB_UPLOAD_DIR\), e\.file_name\)\]\)[ \t]*$", re.M)
    if len(rx_dl.findall(out)) != 1:
        err(rel, "livraison du fichier envoye introuvable (ImagePicker._on_upload)")
        return None, None
    out = rx_dl.sub(lambda m: (
        f"{m.group(1)}_p = os.path.join(str(WEB_UPLOAD_DIR), os.path.basename(str(e.file_name)))\n"
        f"{m.group(1)}self._deliver([_p])\n"
        f"{m.group(1)}try:\n"
        f"{m.group(1)}    os.remove(_p)  # le fichier temporaire n'est plus utile\n"
        f"{m.group(1)}except OSError:\n"
        f"{m.group(1)}    pass"), out)
    rx_cls = re.compile(r"^(_PICKERS\b.*)$", re.M)
    if len(rx_cls.findall(out)) != 1:
        err(rel, "ligne '_PICKERS' introuvable")
        return None, None
    out = rx_cls.sub(lambda m: HELPER + m.group(1), out, count=1)
    return out, "ok"


# ------------------------------------------------------------------------ main
def main():
    # fichiers a analyser
    # seuls main.py et les dossiers de l'application sont analyses (pas les scripts d'outils)
    targets = ["main.py"] if os.path.isfile(os.path.join(ROOT, "main.py")) else []
    for top in ("components", "services", "views"):
        base = os.path.join(ROOT, top)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.startswith(".")]
            for f in fn:
                if f.endswith(".py"):
                    rel = os.path.relpath(os.path.join(dp, f), ROOT)
                    if rel not in SKIP_FILES:
                        targets.append(rel)

    report = []
    for rel in sorted(targets):
        crlf, text = read(rel)
        cur = text
        did = []
        if "from services.auth import Session" in cur or "class _LazySession" in cur:
            res = patch_session(rel, cur)
            if res is not None:
                cur = res
                did.append("Session par visiteur")
        base = os.path.basename(rel)
        specific = {"i18n.py": patch_i18n, "home_view.py": patch_home,
                    "auth_view.py": patch_auth_view, "widgets.py": patch_widgets}.get(base)
        if specific and os.path.dirname(rel) in ("services", "views", "components"):
            res, status = specific(rel, cur)
            if res is not None and status == "ok":
                cur = res
                did.append({"i18n.py": "langue par visiteur", "home_view.py": "filtres par visiteur",
                            "auth_view.py": "brouillon d'inscription par visiteur",
                            "widgets.py": "envois de fichiers securises"}[base])
        if cur != text:
            new_files[rel] = (cur, crlf)
            report.append(f"  corrige {rel} : {', '.join(did)}")

    # fichiers attendus absents => on previent (pas bloquant)
    for must in (os.path.join("services", "i18n.py"), os.path.join("views", "home_view.py"),
                 os.path.join("views", "auth_view.py"), os.path.join("components", "widgets.py"),
                 "main.py"):
        if not os.path.isfile(os.path.join(ROOT, must)):
            err(must, "fichier introuvable")

    if errors:
        print("ECHEC : vos fichiers different de la version attendue, RIEN n'a ete modifie :")
        print("\n".join(errors))
        sys.exit(1)
    if not new_files:
        print("Rien a faire : deja applique.")
        sys.exit(3)
    print("\n".join(report + notes))
    for rel, (text, crlf) in new_files.items():
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8", newline="") as f:
            f.write(text.replace("\n", "\r\n") if crlf else text)
    sys.exit(0)


main()
