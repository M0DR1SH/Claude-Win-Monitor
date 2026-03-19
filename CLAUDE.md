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

## Build exécutable Windows (roadmap)

> Voir `ROADMAP-EXECUTABLE.md` pour la roadmap détaillée.

### Décisions techniques arrêtées

- **Compilateur : Nuitka** (`--standalone`) — produit un vrai binaire natif, réduit les faux positifs antivirus
- **PyInstaller `--onefile` : rejeté** — comportement de "dropper" → détection antivirus massive
- **Installateur : Inno Setup** — installe dans `C:\Program Files`, raccourcis, désinstallation propre
- **Mise à jour : manuelle** — pas de mécanisme automatique ; distribution par l'auteur
- **Extension Chrome : mode non empaqueté** — procédure "Mode développeur" documentée dans le guide

### Chemin du JSON (modification obligatoire avant build)

Le `CONFIG_FILE` **doit** pointer vers `%LOCALAPPDATA%\Claude-Win-Monitor\` :
- `C:\Program Files` est protégé en écriture → "Access Denied" sans cette correction
- Le JSON est ainsi préservé automatiquement lors des réinstallations

```python
from pathlib import Path
import sys, os

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("LOCALAPPDATA", APP_DIR)) / "Claude-Win-Monitor"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "claude_monitor_config.json"
```

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
