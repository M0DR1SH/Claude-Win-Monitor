# Claude Win Monitor

Moniteur de quotas Claude en temps réel pour Windows.
Affiche la consommation de session (5h), hebdomadaire (7j) et le budget mensuel.

**Version courante : v1.8.4**

---

## Installation (version compilée)

1. Lancer `Claude-Win-Monitor-Setup.exe`
2. Si Windows affiche "Windows a protégé votre ordinateur" → **Informations complémentaires** → **Exécuter quand même**
3. Installer l'extension Chrome (voir le Guide d'installation inclus)

## Alertes antivirus — faux positifs

L'exécutable est compilé avec **Nuitka** (Python → binaire natif C). Malgré cela, certains antivirus
le détectent par erreur (heuristique générique sur les binaires compilés depuis Python).

**Scan VirusTotal du Setup (0/71) :** https://www.virustotal.com/gui/file/37ee2d1c23e8b1514540e28a50d99416b6fa060807907cbec77a624f22f88f9f/

### Windows Defender / SmartScreen
- **SmartScreen** : message "Windows a protégé votre ordinateur" au premier lancement.
  → Cliquer **Informations complémentaires** puis **Exécuter quand même**.
- **Windows Defender** : si quarantaine, restaurer le fichier et ajouter une exclusion sur le dossier d'installation.

### ESET Internet Security (testé v19.0.14.0)
ESET peut détecter et mettre en quarantaine l'exe à l'installation ou au premier lancement.

**Procédure de déblocage :**
1. Ouvrir ESET → **Outils** → **Quarantaine**
2. Sélectionner `ClaudeWinMonitor.exe` → **Restaurer**
3. Créer une règle de non-détection : **Configuration** → **Exclusions** → ajouter le chemin d'installation

### Autres antivirus
Si votre antivirus signale le fichier, la procédure est identique :
1. Restaurer depuis la quarantaine
2. Ajouter le dossier d'installation en exclusion

> **Pourquoi ces faux positifs ?**
> L'application n'est pas signée numériquement (certificat Authenticode). Les antivirus appliquent
> une heuristique plus agressive sur les exécutables non signés et inconnus.
> Le code source est entièrement disponible dans ce dépôt pour vérification.

---

## Prérequis

- Windows 10 / 11 (64 bits)
- Google Chrome
- Compte Claude.ai actif

## Développement (mode script)

```bash
pip install customtkinter curl_cffi python-dateutil Pillow pystray
python claude_usage_monitor.py
```

## Architecture

Voir [CLAUDE.md](CLAUDE.md) pour la description détaillée.

## Changelog

Voir [CHANGELOG.md](CHANGELOG.md).
