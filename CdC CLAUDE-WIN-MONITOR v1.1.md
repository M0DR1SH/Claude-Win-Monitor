# CAHIER DES CHARGES – CLAUDE-WIN-MONITOR v1.1

## 0. Portée & conformité

* **Usage** : Outil **read-only** pour consultation de quotas/facturation.
* **Avertissement API** : Endpoints non documentés et susceptibles d’évoluer. L’utilisateur accepte le risque d’instabilité et l’usage à titre personnel, selon les CGU d’Anthropic.
* **OS cible** : Windows 10/11 (x64), mode sombre uniquement (MVP).

---

## 1. Vision & objectifs

### 1.1 Description

Application de bureau native (non-web) affichant en temps réel :

* Fenêtre glissante **5h** (quotas de messages),
* **Hebdomadaire** (si disponible),
* **Facturation/Crédits** (si disponibles),
  sans ouvrir le navigateur.

### 1.2 Philosophie “Set & Forget”

* Démarrage rapide, info critique en **< 2 s**, fonctionnement discret, jamais intrusive.

### 1.3 Cibles

* Développeurs & power users Windows, abonnés Pro/Team/Enterprise, utilisateurs API surveillant budget.

---

## 2. Spécifications fonctionnelles

### 2.1 Session (5h rolling window) — **Priorité haute**

* **Affichages** : jauge + % utilisé ; “X restants / Y totaux” si exposé ; **reset local** (conversion UTC → locale).
* **Codes couleur** :

  * 🟢 **Safe** < 50% (`#6FD771`)
  * 🟡 **Warning** 50–80% (`#F0A24C`)
  * 🔴 **Critical** > 80% (`#EB564F`)

### 2.2 Hebdomadaire — **Priorité moyenne**

* **Affichage** : jauge + % hebdo, reset hebdo si disponible.
* **Donnée absente** : état **“N/A”** propre ou carte masquée (aucune erreur).

### 2.3 Facturation & crédits — **Priorité moyenne**

* **Extra usage** : “consommé / plafond” (ex. `15.50 / 25.00 $`).
* **Crédits API** : solde prépayé affiché tel quel.
* **Devise** : afficher **telle que renvoyée** (USD/EUR), pas de conversion.

### 2.4 Paramètres & configuration

* **Authentification** : saisie manuelle du **cookie `sessionKey`** (ex. `sk-ant-sid01…`).
* **Organisation** : auto-sélection de la première (MVP) ; sélecteur en V2.
* **Rafraîchissement** : auto (par défaut **5 min**, configurable) + bouton **Refresh**.

### 2.5 Résilience & erreurs

* **401/403** : bannière rouge **“Re-login required”**, **arrêt immédiat** de l’auto-refresh.
* **429** : **“Rate-limited”**, backoff et reprise auto.
* **5xx/Parsing** : **“Maintenance/N/A”**, conservation de la dernière valeur connue (grisée).
* **Jamais de crash** (no “app not responding”).

---

## 3. Spécifications techniques

### 3.1 Stack

* **Langage** : Python **3.10+**
* **GUI** : CustomTkinter (dark, coins arrondis, DPI-aware)
* **Réseau** : `requests.Session()` (keep-alive)
* **Packaging** : PyInstaller (one-file .exe)
* **Concurrence** : `threading.Thread` pour les appels réseau (UI non bloquée)

### 3.2 Architecture (MVC light)

* **domain/** : calculs (% utilisé, couleurs par seuils 0.5/0.8, conversion horaire locale).
* **api/** : client HTTP (headers, cookie, timeouts), méthodes :

  * `get_organizations()`
  * `get_stats(org_uuid)` → `message_limit.{remaining, quantity, resets_at}`, `weekly?`
  * `get_billing(org_uuid)` → `plan`, `extra_usage?`, `credits?`
  * Parsing **défensif** (`.get()`), gestion **401/403/429/5xx**.
* **ui/** :

  * `app.py` (fenêtre principale 360×550, dark)
  * `components.py` (cards Session/Weekly/Billing + footer Settings/Refresh/Quit)
  * Thread réseau + file d’événements (after-callback).

### 3.3 Stockage local

* **Fichier** : `config.json` (AppData/Local/ClaudeMonitor ou à côté de l’exe “portable”).
* **Contenu** :

  * `session_key` (V1 : encodage Base64 + **avertissement** ; V2 : **DPAPI**/Windows Credential Locker)
  * `refresh_interval_min` (int)
  * `selected_org_id` (UUID)
  * `logging`, `network` (voir schéma §6.2)

### 3.4 Endpoints cibles (susceptibles d’évoluer)

* Org : `GET https://api.claude.ai/api/organizations`
* Stats : `GET https://api.claude.ai/api/organizations/{uuid}/stats`

  * Clés critiques : `message_limit.remaining`, `message_limit.quantity`, `message_limit.resets_at`
* Billing : `GET https://api.claude.ai/api/organizations/{uuid}/billing/subscription` (ou `/usage` si exposé)

  * Clés : `credits.balance`, `usage`/`extra_usage`

---

## 4. Design UI/UX

### 4.1 Charte

* **Dark mode** only.
* **Fond fenêtre** : `#1e1e1e`, **cartes** : `#2b2b2b`, **typo** : Segoe UI / Roboto / Arial.
* **Dimensions** : **360×550 px**, non redimensionnable.

### 4.2 Palette (barres/progress)

* Vert `#6FD771` / Jaune `#F0A24C` / Rouge `#EB564F`.

### 4.3 Layout

* **Header** : logo + “Claude Usage” + badge d’état.
* **Cards** : Session (~120 px), Weekly (~100 px), Billing (~100 px).
* **Footer** : Settings, Quit, Refresh (selon maquette).

### 4.4 Accessibilité

* Police lisible (≥ 12–13 px), focus clavier, contrastes vérifiés, DPI 125–200%.

---

## 5. Non-fonctionnels (NFR)

* **Performance** : 95ᵉ centile **< 2 s** pour un rafraîchissement réussi (réseau < 500 ms).
* **Ressources** : CPU pic < 5%, **RAM < 150 Mo**.
* **Fiabilité** : 0 crash sur **24 h** avec polling à 5 min ; aucun **thread leak**.
* **Sécurité** : aucun secret en clair dans les logs/UI ; masquage du cookie ; stockage chiffré V2.
* **Réseau** : timeouts **connect=3 s**, **read=5 s** ; retries=2 ; backoff exponentiel 0.5→2 s + **jitter** 0–200 ms.
* **Entreprise** : support **proxy** (HTTP(S)_PROXY), certificats d’entreprise, héritage des paramètres système.
* **Internationalisation** : formats date/heure **locale système**, gestion DST, décimaux locaux.

---

## 6. Opération & observabilité

### 6.1 États d’application

* `OK`, `CONNECTING`, `AUTH_EXPIRED(401/403)`, `RATE_LIMITED(429)`, `MAINTENANCE(5xx)`, `SCHEMA_MISMATCH`, `NETWORK_DOWN`, `PARTIAL_DATA`, `OUTDATED_COOKIE`.
* Chaque état → **message clair**, action (stop auto-refresh pour 401/403/429), style visuel (bannière/badge).

### 6.2 Schéma de configuration (exemple)

```json
{
  "session_key": "…",
  "refresh_interval_min": 5,
  "selected_org_id": null,
  "logging": { "level": "INFO", "max_files": 3, "max_size_mb": 3 },
  "network": {
    "timeout_connect_s": 3,
    "timeout_read_s": 5,
    "retries": 2,
    "backoff_initial_s": 0.5,
    "jitter_ms": 200,
    "proxy": null
  }
}
```

### 6.3 Journalisation

* **Rotation** (taille/nombre), niveaux **INFO/WARN/ERROR**.
* Logs de diag locaux (offline) : dernier succès (horodatage), **latence**, dernier **code HTTP**, **compteur d’échecs**.
* **Aucun secret** dans les logs ; cookie toujours masqué.

---

## 7. Tests & critères de recette

### 7.1 Unitaires

* Calculs de % (bornes 0/100, division par zéro), **seuils couleur**, conversion UTC→locale (incl. DST).
* Parsing défensif : clés absentes/renommées → pas d’exception non gérée.

### 7.2 Intégration

* Fixtures JSON multiples (schémas divergents), latences simulées, erreurs HTTP (401/403/429/5xx).
* Reprise après **veille** : timer relancé, refresh immédiat au “resume”.

### 7.3 UI

* États visuels : OK, N/A, AUTH_EXPIRED, RATE_LIMITED, PARTIAL_DATA.
* Bouton **Refresh** : déclenche un cycle sans geler l’UI.

### 7.4 Acceptation (DoD)

* **Nominal** : Session/Weekly/Billing affichés correctement en **< 2 s**, couleurs correctes, reset local exact.
* **401/403** : bannière “Re-login required”, auto-refresh stoppé, **Refresh** désactivé.
* **429** : “Rate-limited”, backoff appliqué, reprise auto.
* **Schéma changeant** : placeholders **N/A**, UI stable, aucune stacktrace en prod.
* **Packaging** : .exe autonome OK sur Windows vierge, icône affichée.

---

## 8. Roadmap (phases)

1. **Phase 0 – Investigation (“Scanner”)**
   Script CLI brut utilisant `sessionKey`, interroge endpoints, **dump JSON** → verrouiller les champs réellement exposés sur votre compte.

2. **Phase 1 – Backend (api/domain) + tests**
   Client HTTP, calculs, parsing défensif, tests unitaires/intégration.

3. **Phase 2 – UI (MVP)**
   Fenêtre 360×550, cartes statiques, liaison thread réseau → mise à jour UI, états/erreurs.

4. **Phase 3 – Packaging & QA**
   PyInstaller (one-file), icône .ico multi-résolutions, tests sur Windows propre (DPI, proxy).

**V2 (évolutions candidates)** : DPAPI/Credential Locker, sélecteur d’organisation, **tray icon** (tooltip % & reset, menu contextuel), auto-update manuel guidé, auto-start optionnel.

---

## 9. Risques & parades

* **Volatilité endpoint/JSON** → couche `api` isolée, tests “contract snapshot”, fallback **N/A**.
* **Blocage/rate-limit** → backoff strict + arrêt auto-refresh sur 401/403/429.
* **Environnements d’entreprise** → proxy/certificats/timeout configurables.
* **Sécurité locale** → logs épurés, chiffrement stockage **V2**, droits NTFS minimaux.

---

## 10. Annexes

### 10.1 Design tokens

* Couleurs : `#1e1e1e`, `#2b2b2b`, **Vert** `#6FD771`, **Jaune** `#F0A24C`, **Rouge** `#EB564F`.
* Typo : Segoe UI / Roboto / Arial.
* Rayons : cartes **corner_radius=15**.

### 10.2 Ressources

* **Icône** : `.ico` multi-résolutions ; `resource_path()` pour compatibilité PyInstaller ; **fallback** si absent.

---

**Statut** : ✅ **Prêt pour signature et mise en œuvre MVP.**
