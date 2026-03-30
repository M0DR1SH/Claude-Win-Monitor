# CHANGELOG — Claude-Win-Monitor

## v1.9.1 — Guide d'installation bilingue HTML — 30/03/2026

### Guide d'installation (Phase 5 — rework complet)

- **`guide_installation/01-INSTALLATION.html`** — guide unique bilingue FR/EN (remplace `.md` + `.html` + `.pdf` séparés)
- **Toggle FR/EN** sticky en haut de page avec drapeaux PNG natifs (`flag-fr.png`, `flag-en.png`)
- **Sidebar "Sur cette page / On this page"** sticky à droite — suivi de position au scroll avec états : passé (atténué), courant (orange), à venir (gris)
- **13 sections** complètes : prérequis, archive, antivirus, installation, exclusion AV, fenêtre principale, extension navigateur, premier lancement, paramètres, informations, icône tray, mise à jour, désinstallation
- **Illustrations** : boutons à taille réelle (56×56 px pour la barre du bas, 26px inline), badges sync_ok/sync_pb, captures installation + extension
- **Footer** avec 3 icônes cliquables + tooltips (IA Mastery, Profil LG, Buy Me A Coffee)
- **Favicon** `favicon.ico`
- **`_open_guide()`** mis à jour : pointe vers `guide_installation/01-INSTALLATION.html#fr-7` (ou `#en-7`) — ancre directe sur la section "Extension navigateur"
- **Nuitka** : `--include-data-dir="guide_extension=guide_extension"` remplacé par `--include-data-dir="guide_installation=guide_installation"`
- Fichiers obsolètes supprimés : `guide_installation/Guide d'installation.md/.html/.pdf`

---

## v1.9.1 — Interface multilingue & devises — 28/03/2026

### Internationalisation (i18n)

- **Interface multilingue** : FR / EN / DE / IT / ES — sélecteur dans les Paramètres avec drapeaux 28×20 px
- **Sélecteur de devise** : €, $ ou symbole libre (1–3 caractères) — entrée limitée par `validatecommand`
- **Fichier `translations.json`** externe (52 clés × 5 langues) — chargé au démarrage via `class I18n`
- **Redémarrage automatique** à la validation des paramètres — compatible script et exe Nuitka (`subprocess.Popen + sys.exit`)
- **Formatage des dates et durées** entièrement localisé (noms de jours/mois via `I18n`)
- **Menu tray** localisé (Afficher / Actualiser / Quitter)
- **InfoDialog** : lien auteur préfixé `↗ ` pour cohérence avec la fenêtre Paramètres
- **Build Nuitka** : ajout `--include-data-files` pour `translations.json` + 5 drapeaux PNG

---

## v1.8.4 — build exécutable Windows — 19-20/03/2026

### Packaging (Phases 1–3)

#### Phase 1 — Corrections code source

- **`CONFIG_FILE`** : déplacé vers `%LOCALAPPDATA%\Claude-Win-Monitor\claude_monitor_config.json`
  via `_DATA_DIR` (évite "Access Denied" dans `C:\Program Files` protégé en écriture)
- **`sys.frozen`** : détection mode Nuitka compilé vs mode dev pour `_HERE` et `_DATA_DIR`
- **`_set_window_icon`** : priorité au `.ico` racine avant les chemins `work/` (non inclus dans le build)
- **`_open_guide`** : utilise `_HERE` au lieu de `__file__` (fix chemin en mode compilé)
- **`Tooltip._show`** : `wm_attributes("-topmost", True)` — tooltips visibles au-dessus de la fenêtre épinglée

#### Phase 2 — Build Nuitka

Commande retenue : `--standalone --windows-console-mode=disable --enable-plugin=tk-inter --mingw64 --lto=no`

**Problèmes rencontrés et résolus :**
- `--include-data-files` : format `source=destination` requis (pas `source=.`)
- Zig `selfExePath: FileNotFound` : Windows Store Python 3.13 incompatible → Python 3.12 CPython official + `--mingw64`
- `--windows-icon-from-ico` : bloqué par Windows Defender en post-processing → supprimé
- `--lto=yes` (défaut) : build >6 min + blocage Defender → `--lto=no`
- `guide_extension/` manquant du dist → ajout `--include-data-dir="guide_extension=guide_extension"`
- ESET met en quarantaine le dist après build → ajouter exclusion sur `build/` avant de compiler

Résultat : `build/claude_usage_monitor.dist/ClaudeWinMonitor.exe` — ~23 MB, 983 fichiers

#### Phase 3 — Installateur Inno Setup

Script : **`Claude-Win-Monitor.iss`** (racine du dépôt)

**Assets graphiques :** bannière 164×314 (`work/INSTALL-bannière.png`), header (`work/INSTALL-header.png`), icône `.ico`

**Corrections apportées au script :**
- Icône raccourcis : `.ico` copié séparément dans `{app}` (exe sans icône intégrée, Defender bloquait `--windows-icon-from-ico`)
- `UninstallDisplayIcon` → pointe vers `{app}\Claude-Win-Monitor.ico` (pas l'exe) → icône visible dans Paramètres → Applications
- Extension Chrome et PDF/MD du guide exclus de l'installateur → distribués séparément dans l'archive ZIP
- `--windows-console-mode=force` utilisé temporairement pour diagnostiquer silences au lancement → production = `disable`

**Validé :**
- Installation `C:\Program Files (x86)\Claude-Win-Monitor`
- Raccourcis Bureau + Menu Démarrer avec icône
- Icône dans Paramètres → Applications installées (v1.8.4 | Laurent Gérard | 58,7 Mo)
- JSON `%LOCALAPPDATA%\Claude-Win-Monitor\` préservé lors désinstallation/réinstallation
- Toutes les fonctions de l'app opérationnelles depuis l'exe installé

#### Phase 4 — VirusTotal + soumissions antivirus

- **Métadonnées PE** (`--company-name`, `--product-name`, `--file-version`, `--product-version`, `--file-description`, `--copyright`) ajoutées au build Nuitka → 6/71 réduit à 2/69
- **Setup.exe : 0/71** (VirusTotal) — SHA-256 : `37ee2d1c...` — lien ajouté au README
- **Soumissions faux positifs ESET** : `samples@eset.com` (correction immédiate) + `whitelist@eset.sk` (whitelisting éditeur versions futures) — accusés de réception obtenus
- ESET local (moteur 32868/20260319) : **0 détection** sur l'exe installé

#### Phase 5 — Guide d'installation

**Fichier :** `guide_installation/Guide-Installation.md`

Guide illustré en français pour utilisateurs non techniques, 10 sections :
- Prérequis, antivirus (désactiver + exclusion), SmartScreen, installation pas à pas
- Extension navigateur compatible Chrome (Arc, Edge, Brave, Chrome)
- Premier lancement, connexion automatique, affichage quotas
- Icône tray : icône masquée (Paramètres Personnalisation), survol Session%,
  clic gauche, punaise premier plan, info-bulles
- Mise à jour (config préservée), désinstallation

**Images intégrées :** install00–06/09/10, extension01–03, survol_icone (13 captures)
**PDF :** à générer (Typora ou impression navigateur)

---

## v1.8.4 — UI Layout — 18/03/2026

### UI Layout refactorisé (corrections exhaustives)

#### Problématique initiale
L'interface affichait un espace vide énorme entre les cartes de quotas et la barre du bas, rendant le 3e card (Budget) invisible. Les tentatives de calcul dynamique de hauteur via `winfo_reqheight()` ont toutes échoué (CTkTk/customtkinter ne retourne que la taille allouée, pas le minimum du contenu).

#### Solutions finales implémentées

**1. Taille fixe 380×592 pixels** (au lieu de calcul dynamique)
- Valeur analytiquement calculée et confirmée par utilisateur
- Centrée à l'écran dans `__init__()` (pas de recalculs dynamiques)
- Élimine tous les artefacts de mesure de customtkinter

**2. Pack order réorganisé (top→bottom naturel)**
- AVANT : `bottom.pack(side="bottom")` créait un gap entre content et bottom
- APRÈS : tous les widgets packés dans l'ordre top→bottom sans `side="bottom"`
- Root avec `fill="x"` uniquement (pas `expand=True`)
- Ordre : titlebar → separator → header → separator → cards → bottom
- Résultat : stacking naturel, sans espace résidu

**3. Suppression des calculs dynamiques**
- Méthode `_fit_and_center()` dépréciée (remplacée par `_center_window()` utility)
- Plus d'appels à `self.after(100, self._fit_and_center)`
- Plus de `self.update()` qui déclenchait des callbacks cascadés
- Plus de `winfo_reqheight()` sur root ou fenêtre

#### Code changes
- `__init__()` : géométrie fixe 380×592 + centrage au démarrage
- `create_ui()` : pack order réorganisé, commentaires exhaustifs
- `_make_card()` : documentation complète de la structure et footer 2-col
- `_center_window()` : dépréciée (legacy si recentrage futur)
- `CLAUDE.md` : ajout section "UI Layout (v1.8.4+)" détaillée

#### Résultats
✅ Les 3 cartes de quotas sont maintenant visibles
✅ Barre du bas fixée à 56px (plus de démesure)
✅ Fenêtre compact et centré, sans gap, hauteur stable
✅ Code plus clair avec commentaires exhaustifs

---

## v1.8.3 — 01/03/2026

### Nouveau
- **UX** Tray "Afficher" et "Actualiser" : fenêtre forcée au premier plan (`_bring_to_front` — deiconify + topmost temporaire + lift + focus_force)

### Corrections
- **UI** SettingsDialog : hover des boutons liens plus visible (vert `#0b2115→#1e4d2e`, bleu `#0d1f3c→#1a3a5c`)

### Corrections exhaustives (analyse de projet)
- `generate_pdf.py` : noms de fichiers corrigés (`GUIDE-SESSION-KEY.*` → `Guide d'installation.*`)
- `extension/background.js` : `localhost` → `127.0.0.1` (cohérence avec le receiver Python)
- `extension/manifest.json` : version `1.0` → `1.8.3`, date mise à jour, host `127.0.0.1`
- `claude_usage_monitor.py` : `_HERE` pour chemins absolus des icônes (indépendant du CWD)
- `claude_usage_monitor.py` : `_session_expired` flag → stoppe `background_loop` sur 403 + ouvre Paramètres
- `claude_usage_monitor.py` : `_on_new_session_key` — vérification `if is not None` + reset `_session_expired`
- `claude_usage_monitor.py` : `reload_app()` reset `_session_expired`
- `claude_usage_monitor.py` : `do_POST` — ajout `OSError` dans except
- `claude_usage_monitor.py` : suppression `print(e)` dans `init_sequence`
- `claude_usage_monitor.py` : suppression section fantôme "ICÔNE DE STATUT"
- `CHANGELOG.md` : v1.7.2 simplifié, suppression duplication avec v1.8.0

---

## v1.8.2 — 01/03/2026

### Corrections (revue de code)
- **Suppression** classe `StatusIcon` inutilisée (code mort)
- **Bug** `self._settings_dialog` non initialisé → `AttributeError` potentielle → initialisé à `None` dans `__init__()`
- **Bug** `self.config["session_key"]` → `KeyError` si config vide → remplacé par `.get("session_key", "")`
- **Bug** `json.loads()` et `int(Content-Length)` sans protection → ajout try/except dans `do_POST()`
- **Bug** `fetch_data()` : `r_limit` et `r_prepaid` non vérifiés avant appel à `update_ui()` → vérification des 3 statuts HTTP
- **UI** Titlebar des fenêtres modales sans gras (`bold` retiré) — `🅻🅶` lisible
- **UI** `APP_AUTHOR` sans gras dans la fenêtre À propos

### Refactoring
- Renommage `app.py` → `claude_usage_monitor.py` (aligné avec `APP_NAME`)
- `.claude/` exclu du repo git (config locale Claude Code)

---

## v1.8.1 — 28/02/2026

### Fenêtre Paramètres redessinée
- Deux sections distinctes : ① Méthode automatique (vert) + ② Méthode manuelle (bleu)
- Lien vers le guide d'installation local (`guide_extension/Guide d'installation.html`)
- Lien vers `claude.ai` pour récupération manuelle via F12
- Hauteur auto-calculée via `winfo_reqheight()` — boutons toujours visibles
- Polices agrandies (11→12pt, bouton 12→13pt)

### Guide d'installation
- `guide_extension/Guide d'installation.html` — thème dark, 4 étapes illustrées
- `guide_extension/Guide d'installation.pdf` — généré via Playwright (`emulate_media("screen")`)
- `guide_extension/generate_pdf.py` — script de génération
- Images redimensionnées à 80% pour le rendu PDF

### Commentaires & documentation
- Commentaires complets sur toutes les classes et méthodes de `claude_usage_monitor.py`
- `CHANGELOG.md` créé
- `.gitignore` créé

---

## v1.8.0 — 28/02/2026

### Nouveau : authentification automatique via extension navigateur

**Contexte**
L'authentification reposait jusqu'ici sur un copier-coller manuel de la `sessionKey`
depuis les DevTools du navigateur. Cette session explore des alternatives automatiques.

---

### Recherches d'authentification — résultats

#### Token CLI Claude Code (`sk-ant-oat01-...`) — ÉCARTÉ
- Fichier source : `~/.claude/.credentials.json` → `claudeAiOauth.accessToken`
- Headers requis : `anthropic-beta: oauth-2025-04-20`, `User-Agent: claude-code/2.1.5`
- Endpoint fonctionnel : `https://api.anthropic.com/api/oauth/usage`
  → retourne `five_hour`, `seven_day`, `extra_usage` (utilisation en %)
- **Bloqué** sur `claude.ai` → HTTP 403 sur tous les endpoints (durcissement Anthropic, jan 2026)
- **Manquant** : solde prépayé (`prepaid/credits`) → introuvable sur api.anthropic.com
- Décision : écarté tant que le solde prépayé n'est pas accessible

#### Lecture directe cookies Chrome/Edge — ABANDONNÉE
- Chrome verrouille exclusivement son fichier SQLite `Cookies`
- Tentatives : SQLite URI `immutable=1`, ctypes `CreateFileW`, `robocopy /B`, `browser_cookie3`
- Toutes échouent sans droits administrateur (VSS requis)

#### Extension navigateur + receiver HTTP — RETENUE ✅
Solution retenue : zéro friction utilisateur, données complètes.

### Extension navigateur (`extension/`)
- `manifest.json` — Manifest V3, permissions `cookies` + `tabs`
- `background.js` — service worker, retry 10×5s, polling `/ping` toutes les 10s
- Déclencheurs : `onInstalled`, `onStartup`, `cookies.onChanged`, `tabs.onUpdated`

### Receiver HTTP (`claude_usage_monitor.py`)
```
_SessionKeyHandler :
  GET  /ping          → {"status":"ready"}
  POST /session-key   → reçoit la clé, déclenche reload automatique
  OPTIONS             → headers CORS
```

### Flux complet
```
Démarrage app  →  receiver HTTP actif sur localhost:27182
Extension      →  détecte l'app via GET /ping (toutes les 10s)
               →  envoie POST /session-key avec sessionKey de claude.ai
App            →  reçoit la clé → ferme dialog Paramètres → reload → stats affichées
```

---

## v1.7.1 et antérieur

Authentification manuelle uniquement : copier-coller de la `sessionKey` depuis les DevTools
du navigateur (F12 › Application › Cookies › https://claude.ai › sessionKey).
Les recherches menées pour automatiser cette étape sont documentées dans **v1.8.0**.

---

## v1.7.1 et antérieur

Authentification manuelle par copier-coller de la `sessionKey` dans la fenêtre Paramètres.
