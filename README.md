# Claude Win Monitor

Moniteur de quotas Claude en temps réel pour Windows.
Affiche la consommation de session (5h), hebdomadaire (7j) et le budget mensuel.

**Auteur :** Laurent Gérard
**Version courante : v1.9.1**
**Licence :** open source — code source intégralement disponible dans ce dépôt

---

## Description

Claude Win Monitor est une application de bureau Windows qui interroge l'API de
[claude.ai](https://claude.ai) pour afficher en temps réel la consommation de quotas
d'un compte Claude Pro ou Team.

**Ce que fait l'application :**
- Se connecte à `claude.ai` via une clé de session transmise par une extension navigateur
- Interroge les endpoints d'usage de l'API Claude (quotas, budget, crédits prépayés)
- Affiche les données dans une fenêtre compacte avec icône dans la barre des tâches

**Ce que l'application ne fait pas :**
- Aucune collecte de données personnelles
- Aucune communication vers des serveurs tiers (uniquement vers `claude.ai`)
- Aucune modification du système, aucune persistance au démarrage automatique

---

## Installation (version compilée)

1. Lancer `Claude-Win-Monitor-Setup.exe`
2. Si Windows affiche "Windows a protégé votre ordinateur" → **Informations complémentaires** → **Exécuter quand même**
3. Installer l'extension navigateur (voir le Guide d'installation inclus)

---

## Alertes antivirus — faux positifs

L'exécutable est compilé avec **Nuitka** (Python → binaire natif C). Certains antivirus
détectent par erreur les binaires compilés depuis Python via heuristique générique.

**Scan VirusTotal du Setup (0/71) :**
https://www.virustotal.com/gui/file/37ee2d1c23e8b1514540e28a50d99416b6fa060807907cbec77a624f22f88f9f/

**Hashes de référence (v1.8.4) :**

| Fichier | SHA-256 |
|---------|---------|
| `Claude-Win-Monitor-Setup.exe` | `37ee2d1c23e8b1514540e28a50d99416b6fa060807907cbec77a624f22f88f9f` |
| `ClaudeWinMonitor.exe` | `c1cf5cfef1b0afa55e60cdec05fa338ce7f13fdccd72ec6a9563258882ead449` |

### Windows Defender / SmartScreen
- **SmartScreen** : cliquer **Informations complémentaires** → **Exécuter quand même**
- **Windows Defender** : restaurer depuis la quarantaine + ajouter une exclusion sur le dossier d'installation

### ESET Internet Security (testé v19.0.14.0)
ESET peut détecter `ClaudeWinMonitor.exe` comme `Python/Packed.Nuitka_AGen` (faux positif).
Une soumission de faux positif a été envoyée à `samples@eset.com` et `whitelist@eset.sk` (20/03/2026).

**Procédure de déblocage :**
1. ESET → **Outils** → **Quarantaine** → sélectionner `ClaudeWinMonitor.exe` → **Restaurer**
2. ESET → **Configuration** → **Exclusions** → ajouter `C:\Program Files (x86)\Claude-Win-Monitor`

### Autres antivirus
Restaurer depuis la quarantaine et ajouter le dossier d'installation en exclusion.

> **Pourquoi ces faux positifs ?**
> L'application n'est pas signée numériquement (certificat Authenticode).
> Les antivirus appliquent une heuristique plus agressive sur les exécutables non signés.
> **Le code source est intégralement disponible dans ce dépôt pour vérification.**

---

## Prérequis

- Windows 10 / 11 (64 bits)
- Navigateur compatible Chrome (Google Chrome, Edge, Arc, Brave…)
- Compte Claude.ai actif (Pro ou Team)

---

## Développement (mode script)

```bash
pip install customtkinter curl_cffi python-dateutil Pillow pystray
python claude_usage_monitor.py
```

Code source principal : [`claude_usage_monitor.py`](claude_usage_monitor.py)

---

## Architecture

Voir [CLAUDE.md](CLAUDE.md) pour la description détaillée.

## Changelog

Voir [CHANGELOG.md](CHANGELOG.md).

## Assistance

Communauté : [IA Mastery](https://www.skool.com/ia-mastery)
