# ROADMAP — Claude-Win-Monitor : Build Exécutable Windows

> Version cible : v1.8.4
> Date de rédaction : 2026-03-19
> Statut : **À faire**

---

## Contexte et décisions techniques

### Outil de compilation : Nuitka (retenu)
- Traduit Python → C → binaire natif (DLLs `.pyd`)
- Élimine le comportement d'extraction en mémoire (contrairement à PyInstaller `--onefile`)
- Réduit drastiquement les faux positifs antivirus (pas de "dropper" comportemental)
- Mode : `--standalone` (équivalent `--onedir` de PyInstaller)

### PyInstaller `--onefile` : explicitement rejeté
- Décompresse dans `%TEMP%\_MEIxxxx` à chaque lancement
- Imite le comportement d'un malware ("dropper") → détection massive par antivirus
- Casse la gestion des chemins pour les données persistantes

### Installateur : Inno Setup
- Installe dans `C:\Program Files\Claude-Win-Monitor`
- Crée raccourcis Bureau + Menu Démarrer
- Gère la désinstallation propre
- **Ne touche jamais `%LOCALAPPDATA%`** → JSON préservé lors des mises à jour

### Fichier JSON de configuration
- **Emplacement actuel (à corriger)** : chemin relatif `"claude_monitor_config.json"` → écrit dans le répertoire courant
- **Emplacement cible** : `%LOCALAPPDATA%\Claude-Win-Monitor\claude_monitor_config.json`
- **Raison** : `C:\Program Files` est protégé en écriture → "Access Denied" sans droits admin
- **Avantage** : préservé automatiquement lors des réinstallations / mises à jour

### Sécurité Windows
- **Windows Defender / antivirus** : Nuitka réduit les faux positifs. Si persistance : soumettre via [Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission)
- **SmartScreen** : non résolu par Nuitka. Solution retenue = assumer + documenter ("Informations complémentaires" > "Exécuter quand même")
- **Authenticode (signature)** : non prévu — coût 100-400€/an, hors périmètre

### Mise à jour
- **Pas de mécanisme automatique.** Distribution manuelle par l'auteur.
- Procédure utilisateur : re-lancer le Setup → écrase `Program Files` → JSON dans `LOCALAPPDATA` intact

### Extension Chrome
- Distribution en dossier source (mode non empaqueté)
- Procédure : `chrome://extensions` → Mode développeur → Charger l'extension non empaquetée
- Chrome Web Store : non prévu
- Alerte périodique Chrome ("désactiver les extensions dev") : documenter dans le guide

---

## PHASE 1 — Correction du code source

### 1.1 — Correction des chemins (critique)

**Fichier :** `claude_usage_monitor.py`

**Modification :** Remplacer `CONFIG_FILE = "claude_monitor_config.json"` par :

```python
from pathlib import Path
import sys
import os

if getattr(sys, "frozen", False):
    # Mode packagé (Nuitka standalone)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    # Mode dev
    APP_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.environ.get("LOCALAPPDATA", APP_DIR)) / "Claude-Win-Monitor"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_DIR / "claude_monitor_config.json"
```

**Localisation dans le code :** classe `ConfigManager` — chercher `CONFIG_FILE` et `_HERE`.

### 1.2 — Audit des chemins des ressources PNG

Vérifier que **tous** les `CTkImage(Image.open(...))` utilisent `_HERE` ou un chemin absolu compatible `sys.frozen`. Aucun chemin relatif nu ne doit subsister.

Ressources à vérifier :
- `Claude-Win-Monitor_ICO.png` (logo header)
- `IMG-refresh.png`
- `IMG-engrenage.png`
- `IMG-power-off.png`
- `IMG-information.png`
- `IMG-session.png`
- `IMG-hebdomadaire.png`
- `IMG-portefeuille.png`
- `Claude-Win-Monitor.ico` (icône tray)

### 1.3 — Test en mode dev post-correction

- Lancer `python claude_usage_monitor.py`
- Vérifier que `%LOCALAPPDATA%\Claude-Win-Monitor\claude_monitor_config.json` est créé
- Vérifier que tous les PNG se chargent
- Vérifier que le port 27182 est actif

---

## PHASE 2 — Build Nuitka

### 2.1 — Prérequis

```bash
pip install nuitka
# MinGW64 : Nuitka le propose automatiquement au premier build si MSVC absent
```

### 2.2 — Commande de build

```bash
python -m nuitka \
  --standalone \
  --windows-console-mode=disable \
  --enable-plugin=tk-inter \
  --include-data-files="Claude-Win-Monitor_ICO.png=." \
  --include-data-files="IMG-refresh.png=." \
  --include-data-files="IMG-engrenage.png=." \
  --include-data-files="IMG-power-off.png=." \
  --include-data-files="IMG-information.png=." \
  --include-data-files="IMG-session.png=." \
  --include-data-files="IMG-hebdomadaire.png=." \
  --include-data-files="IMG-portefeuille.png=." \
  --include-data-files="Claude-Win-Monitor.ico=." \
  --windows-icon-from-ico="Claude-Win-Monitor.ico" \
  --output-dir=build \
  --output-filename=ClaudeWinMonitor \
  claude_usage_monitor.py
```

> Résultat attendu : `build/claude_usage_monitor.dist/ClaudeWinMonitor.exe`

### 2.3 — Tests post-build

- [ ] Fenêtre s'ouvre correctement (380×592)
- [ ] PNG / icônes visibles
- [ ] JSON créé dans `%LOCALAPPDATA%\Claude-Win-Monitor\`
- [ ] Port 27182 actif (`netstat -an | findstr 27182`)
- [ ] Tray icon fonctionnel
- [ ] Scan Windows Defender → pas de quarantaine

---

## PHASE 3 — Installateur Inno Setup

### 3.1 — Prérequis

Télécharger Inno Setup 6.x : https://jrsoftware.org/isinfo.php

### 3.2 — Script `.iss` (squelette)

```ini
[Setup]
AppName=Claude Win Monitor
AppVersion=1.8.4
AppPublisher=M0DR1SH
DefaultDirName={autopf}\Claude-Win-Monitor
DefaultGroupName=Claude Win Monitor
OutputBaseFilename=Claude-Win-Monitor-Setup
OutputDir=dist-installer
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "build\claude_usage_monitor.dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Claude Win Monitor"; Filename: "{app}\ClaudeWinMonitor.exe"
Name: "{autodesktop}\Claude Win Monitor"; Filename: "{app}\ClaudeWinMonitor.exe"

[Run]
Filename: "{app}\ClaudeWinMonitor.exe"; Description: "Lancer Claude Win Monitor"; Flags: nowait postinstall skipifsilent

; NOTE : %LOCALAPPDATA%\Claude-Win-Monitor\ n'est PAS géré par l'installateur.
; Le JSON de configuration est préservé automatiquement lors des mises à jour.
```

### 3.3 — Tests installateur

- [ ] Installation complète (chemin par défaut)
- [ ] Raccourcis Bureau + Menu Démarrer créés
- [ ] Application se lance depuis le raccourci
- [ ] JSON créé dans `%LOCALAPPDATA%\Claude-Win-Monitor\` au premier lancement
- [ ] Test de mise à jour simulée : réinstaller → JSON préservé
- [ ] Test de désinstallation : `Program Files` nettoyé, JSON intact

---

## PHASE 4 — Structure du livrable ZIP

```text
Claude-Win-Monitor-v1.8.4.zip
├── 1-Installateur/
│   └── Claude-Win-Monitor-Setup.exe
├── 2-Extension-Chrome/
│   ├── manifest.json
│   ├── background.js
│   └── (autres fichiers de l'extension)
├── 3-Documentation/
│   ├── Guide-Installation.pdf
│   ├── Guide-Installation.md
│   └── 00-LISEZ-MOI.txt
└── VERSION.txt
```

**Contenu de `00-LISEZ-MOI.txt` :**
```
Claude Win Monitor v1.8.4
=========================
ÉTAPES D'INSTALLATION :

1. Lancer : 1-Installateur/Claude-Win-Monitor-Setup.exe
   → Si Windows affiche "Windows a protégé votre ordinateur" :
     cliquer "Informations complémentaires" puis "Exécuter quand même"

2. Suivre le guide : 3-Documentation/Guide-Installation.pdf

3. Installer l'extension Chrome (procédure dans le guide, section 4)
```

---

## PHASE 5 — Guide d'installation

**Format prioritaire :** PDF illustré
**Format secondaire :** Markdown (source versionnable)

| Section | Contenu |
|---------|---------|
| 1. Prérequis | Windows 10/11, Chrome, aucune installation Python requise |
| 2. Installation | Lancer le Setup, captures d'écran étape par étape |
| 3. Alerte SmartScreen | Capture de l'écran bleu + "Informations complémentaires > Exécuter quand même" |
| 4. Extension Chrome | `chrome://extensions` → Mode développeur → Charger → pointer `2-Extension-Chrome/` |
| 5. Alerte Chrome périodique | Comment ignorer les alertes "désactiver les extensions dev" |
| 6. Premier lancement | Ce que l'utilisateur voit, comment ça se connecte automatiquement |
| 7. Mise à jour | Re-lancer le Setup — la configuration est conservée automatiquement |

---

## ORDRE D'EXÉCUTION

```
Phase 1 (code) → Phase 2 (Nuitka build) → Phase 3 (Inno Setup) → Phase 4 (ZIP) → Phase 5 (guide)
     ↑                    ↑
  itérer si            itérer si
  bug chemin           bug build
```
