# CHANGELOG — Claude-Win-Monitor

## v1.7.2 — 28/02/2026

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
- Profil disponible : `/api/oauth/account`, `/api/oauth/profile`
- **Bloqué** sur `claude.ai` → HTTP 403 sur tous les endpoints (durcissement Anthropic, jan 2026)
- **Manquant** : solde prépayé (`prepaid/credits`) → introuvable sur api.anthropic.com
- Décision : écarté tant que le solde prépayé n'est pas accessible

#### Lecture directe cookies Chrome/Edge — ABANDONNÉE
- Chrome verrouille exclusivement son fichier SQLite `Cookies`
- Tentatives : SQLite URI `immutable=1`, ctypes `CreateFileW`, `robocopy /B`, `browser_cookie3`
- Toutes échouent sans droits administrateur (VSS requis)
- Décision : impossible sans élévation de privilèges

#### Extension navigateur + receiver HTTP — RETENUE ✅
Solution retenue : zéro friction utilisateur, données complètes.

---

### Extension navigateur (`extension/`)

Fichiers créés :
- `extension/manifest.json` — Manifest V3, permissions `cookies` + `tabs`
- `extension/background.js` — service worker (lecture cookie + envoi HTTP)
- `extension/icon.png` — icône (créée manuellement)

Comportement :
- Lit `sessionKey` via `chrome.cookies.get()` → inaccessible sans extension (lock Chrome)
- Envoie via `POST http://localhost:27182/session-key`
- Déclencheurs : `onInstalled`, `onStartup`, `cookies.onChanged`, `tabs.onUpdated`
- Retry automatique : jusqu'à 10 × 5s si l'app n'est pas encore lancée
- Polling `/ping` toutes les 10s pour détecter le démarrage de l'app
- Installation : `chrome://extensions` → mode développeur → charger dossier `extension/`
- Peut être désactivée après premier envoi (réactiver uniquement si cookie change)

---

### Modifications `app.py`

#### Ajout : receiver HTTP (port 27182)
```
from http.server import HTTPServer, BaseHTTPRequestHandler

_SessionKeyHandler :
  GET  /ping          → {"status":"ready"}  (heartbeat pour l'extension)
  POST /session-key   → reçoit la clé, déclenche reload automatique
  OPTIONS             → headers CORS

_start_receiver(app) → thread daemon, démarré dans __init__
```

#### Ajout : méthode `_on_new_session_key(key)`
- Sauvegarde la clé dans `claude_monitor_config.json`
- Ferme automatiquement la fenêtre Paramètres si elle est ouverte
- Appelle `reload_app()` pour recharger les stats

#### Modification : `open_settings()`
- Stocke la référence `self._settings_dialog` pour permettre la fermeture automatique

---

### Flux complet (après cette mise à jour)

```
Démarrage app  →  receiver HTTP actif sur localhost:27182
Extension      →  détecte l'app via GET /ping (toutes les 10s)
               →  envoie POST /session-key avec sessionKey de claude.ai
App            →  reçoit la clé → ferme dialog Paramètres → reload → stats affichées
```

Cas couverts :
| Situation | Résultat |
|---|---|
| App lancée, navigateur ouvert | Clé reçue en ≤ 10s |
| App lancée, onglet claude.ai ouvert | Clé reçue immédiatement |
| Navigateur démarre avant l'app | Extension retente jusqu'à 50s |
| Cookie renouvelé par Claude | Envoi et reload automatiques |
| Aucun JSON de config au démarrage | Dialog Paramètres → fermé automatiquement à réception |

---

## v1.7.1 et antérieur

Authentification manuelle par copier-coller de la `sessionKey` dans la fenêtre Paramètres.
