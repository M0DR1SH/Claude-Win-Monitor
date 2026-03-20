# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Lancer l'application

```bash
python claude_usage_monitor.py
```

Aucun système de build. Pas de `requirements.txt` — les dépendances sont à installer manuellement :

```bash
pip install customtkinter curl_cffi python-dateutil Pillow pystray
```

## Architecture

Le projet est un moniteur de quotas Claude en temps réel, composé de deux parties qui communiquent via HTTP local.

### Application Python (`claude_usage_monitor.py`)

Un seul fichier de ~1 200 lignes. Hiérarchie des classes :

- **`ConfigManager`** — lecture/écriture du fichier `claude_monitor_config.json` (session_key, org_id)
- **`_BaseDialog`** — fenêtre modale de base (drag, overlay, titlebar custom). Étendue par `SettingsDialog` et `InfoDialog`
- **`_SessionKeyHandler`** / `_start_receiver()` — serveur HTTP local sur le port `27182` qui reçoit la session key envoyée par l'extension navigateur
- **`ClaudeMonitorApp`** — fenêtre principale customtkinter ; orchestre le cycle fetch → parse → affichage UI

**Flux de données :**
```
Extension navigateur → POST http://127.0.0.1:27182/session-key
  → ClaudeMonitorApp._on_new_session_key()
  → reload_app() → init_sequence() → fetch_data() → update_ui()
```

**APIs consommées (endpoints non documentés de claude.ai) :**
- `/api/bootstrap` — profil utilisateur + org_id
- `/api/organizations/{org_id}/usage` — quotas 5h et 7 jours
- `/api/organizations/{org_id}/overage_spend_limit` — budget mensuel consommé
- `/api/organizations/{org_id}/prepaid/credits` — solde prépayé restant

Les requêtes HTTP utilisent `curl_cffi` avec impersonation Chrome pour éviter le blocage anti-bot.

### Extension navigateur (`extension/`)

Manifest V3. Le service worker `background.js` lit le cookie `sessionKey` sur `claude.ai` et le poste vers l'app Python. Retry : 10 tentatives × 5 s. Polling du `/ping` toutes les 10 s.

## Points clés

- **Pas de tests automatisés.** Le dossier `work/` contient des scripts de développement/expérimentation (non productifs).
- **`pystray` est optionnel** — l'app dégrade gracieusement si absent (pas de tray).
- **Langue** : interface et code en français. Maintenir cette convention.
- **Version courante** : v1.8.4 — voir `CHANGELOG.md` pour l'historique.
- Le fichier `claude_monitor_config.json` est dans `.gitignore` (contient la session key).

## Build exécutable Windows

> Voir `ROADMAP-EXECUTABLE.md` pour la roadmap complète.
> **Statut : Phases 1 ✅ 2 ✅ 3 ✅ — Phases 4-5 à faire (ZIP + guide)**

### État courant (20/03/2026)

- **`build/claude_usage_monitor.dist/ClaudeWinMonitor.exe`** — build Nuitka validé (~23 MB)
- **`dist-installer/Claude-Win-Monitor-Setup.exe`** — installateur Inno Setup validé (~16 MB)
- **`Claude-Win-Monitor.iss`** — script Inno Setup à la racine du dépôt

### Commande de build Nuitka (production)

```bash
# Depuis la racine du projet — Python 3.12 CPython obligatoire (pas Store Python)
"C:\Users\souli\AppData\Local\Programs\Python\Python312\python.exe" -m nuitka \
  --standalone \
  --windows-console-mode=disable \
  --enable-plugin=tk-inter \
  --mingw64 \
  --lto=no \
  --assume-yes-for-downloads \
  --include-data-files="Claude-Win-Monitor_ICO.png=Claude-Win-Monitor_ICO.png" \
  --include-data-files="IMG-refresh.png=IMG-refresh.png" \
  --include-data-files="IMG-engrenage.png=IMG-engrenage.png" \
  --include-data-files="IMG-power-off.png=IMG-power-off.png" \
  --include-data-files="IMG-information.png=IMG-information.png" \
  --include-data-files="IMG-session.png=IMG-session.png" \
  --include-data-files="IMG-hebdomadaire.png=IMG-hebdomadaire.png" \
  --include-data-files="IMG-portefeuille.png=IMG-portefeuille.png" \
  --include-data-files="Claude-Win-Monitor.ico=Claude-Win-Monitor.ico" \
  --include-data-dir="guide_extension=guide_extension" \
  --output-dir=build \
  --output-filename=ClaudeWinMonitor \
  claude_usage_monitor.py
```

> **IMPORTANT avant tout rebuild :** ajouter une exclusion ESET sur `build\` et `dist-installer\`
> (ESET met en quarantaine les fichiers du dist après compilation).

### Commande Inno Setup

Ouvrir `Claude-Win-Monitor.iss` → **Build → Compile** (`F9`).

### Décisions techniques arrêtées

- **Compilateur : Nuitka** (`--standalone`) — binaire natif, réduit les faux positifs antivirus
- **PyInstaller `--onefile` : rejeté** — comportement "dropper" → détection antivirus massive
- **`--windows-icon-from-ico` : supprimé** — Windows Defender bloque le post-processing
- **`--lto=no`** — link ~1 min au lieu de 6+ min, contourne blocage Defender
- **`--mingw64` + Python 3.12 CPython** — Zig incompatible avec Windows Store Python
- **Installateur : Inno Setup** — `C:\Program Files (x86)\Claude-Win-Monitor`, raccourcis, icône
- **JSON config : `%LOCALAPPDATA%\Claude-Win-Monitor\`** — préservé lors des mises à jour
- **Extension Chrome + PDF/MD guide** : exclus de l'installateur, distribués dans l'archive ZIP
- **Authenticode (signature)** : non prévu — hors périmètre

### Prochaines étapes

1. Scan VirusTotal de `Claude-Win-Monitor-Setup.exe`
2. Phase 5 — Guide d'installation illustré (PDF + Markdown)
3. Phase 4 — Archive ZIP + `SHA256SUMS.txt`
4. GitHub Release v1.8.4

## UI Layout (v1.8.4+)

### Dimensionnement et géométrie

**Taille fixe 380×592 pixels** — centrée à l'écran. Après tests exhaustifs, les calculs dynamiques via `winfo_reqheight()` ne fonctionnaient pas sur `CTkTk` (customtkinter wraps tkinter en canvas, ce qui fausse les mesures). **Solution finale : taille fixe analytiquement calculée.**

Décomposition :
- Titlebar : 36px (draggable, logo mini + titre + boutons pin/minimize/close)
- Separator 1 : 1px (gris sombre)
- Header : ~80px (logo 52 + user info + refresh button)
- Separator 2 : 1px (gris clair)
- Cards zone : ~320px (3 cartes × ~100-110px + spacers 10px entre)
- Spacer cards/bottom : 6px
- Bottom bar : 56px (grid layout, 3 boutons + séparateurs)
- Borders/padding : 2px (padx=1, pady=1 du root)
- **Total : 592px**

### Ordre de pack (critique!)

Le root frame pack avec `fill="x"` UNIQUEMENT (pas `expand=True`). Les widgets sont packés dans l'ordre naturel **top → bottom** :

```
root.pack(fill="x", padx=1, pady=1)     ← NO expand=True!
├── titlebar.pack(fill="x")
├── separator.pack(fill="x")
├── header.pack(fill="x")
├── separator.pack(fill="x", pady=...)
├── cards.pack(fill="x", padx=14, pady=...)
└── bottom.pack(fill="x")               ← NO side="bottom"!
    └── 3 buttons en grid (cols 0,2,4 uniform="btn")
```

**IMPORTANT :** Avant cette correction, `bottom.pack(side="bottom")` créait un gap énorme entre les cartes et les boutons quand root avait `expand=True`. Le résidu d'espace était distribué au milieu. **La solution = ordre naturel pack sans side="bottom".**

### Cartes de quotas (v1.8.3+)

Chaque carte (Session / Hebdomadaire / Budget) a la structure :

```
┌─────────────────────────────────────┐
│ 🎨 ICON  Titre gras         NN%     │ ← row (titre + %)
├─────────────────────────────────────┤
│ [██████████░░░░░] progress bar      │ ← barre (height=10)
├─────────────────────────────────────┤
│ Gauche (reset/conso)  Droite (date) │ ← footer 2-col
└─────────────────────────────────────┘
```

- **Suppression des sous-titres** (v1.8.3) — économise ~50px/carte
- **Footer en 2 colonnes** (v1.8.4) : gauche = reset/conso, droite = date/solde
- **Icônes 18×18 PNG** tintées (PIL channel replacement) : session, hebdo, portefeuille
- **Couleurs dynamiques** : vert (<50%), orange (50–80%), rouge (>80%)

### Boutons de la barre du bas

Grid layout avec 3 boutons + 2 séparateurs verticaux :

```
[Settings ⚙] | [Info ℹ] | [Quit ⏻]
```

- **Colonnes 0, 2, 4** : boutons (uniform="btn" = largeur égale)
- **Colonnes 1, 3** : séparateurs (width=1, gris sombre #2a2a2a)
- **Height=56** verrouillé via `pack_propagate(False)`
- **grid_rowconfigure(0, weight=1)** pour flex vertical (mais limité par height=56)
