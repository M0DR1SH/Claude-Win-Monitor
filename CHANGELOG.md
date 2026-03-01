# CHANGELOG — Claude-Win-Monitor

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
