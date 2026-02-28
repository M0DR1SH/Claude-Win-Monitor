1) Stack et modules
- OS cible : Windows 10/11.
- Langage : Python (3.10+).
- UI : bibliothèque d’interface native à cartes avec mode sombre.
- Réseau : client HTTP avec gestion de session et cookies.
- Concurrence : thread dédié pour les appels réseau + file d’événements UI.
- Persistance : fichier de configuration local (JSON) + option coffre système (V2).
- Packaging : binaire autonome (.exe) avec gestion des ressources (icône, images).

2) Architecture logique
- core/config.py : lecture/écriture des préférences (intervalle, org sélectionnée). Schéma validé et défauts sûrs.
- core/secure_store.py : abstraction de stockage secret (V1: fichier config; V2: coffre Windows).
- net/session.py : création de la session HTTP (en-têtes, cookie), retry/backoff, timeouts, proxy (hérite des variables système).
- api/anthropic_client.py :
  - get_organizations() → [ {uuid, name} ]
  - get_stats(org_uuid) → { message_limit: {remaining, quantity, resets_at}, weekly?: {...} }
  - get_billing(org_uuid) → { plan, extra_usage?, credits? }
  - Robustesse : .get() défensifs, 401/403/5xx gérés, schémas faibles.
- domain/calculations.py :
  - compute_percent(remaining, quantity) → % utilisé.
  - estimate_remaining(...) si “remaining” absent.
  - to_local_time(iso_ts) → datetime locale formatée.
  - color_bucket(percent) → {safe|warning|critical}.
- ui/theme.py : palette (fond, cartes, texte, vert #6FD771 / orange #F0A24C / rouge #EB564F), coins arrondis, marges.
- ui/widgets.py :
  - CardSessionUsage, CardWeekly, CardBilling, Footer (Settings/Exit/Refresh).
  - Progress bars/labels/états (N/A, Re-login required).
- ui/controller.py :
  - Orchestration : init, cycle de rafraîchissement (timer), déclenchements (bouton Refresh), FSM d’état (“idle”, “loading”, “ok”, “auth_error”, “maintenance”).
  - Thread réseau : exécute les fetchs, publie les résultats à l’UI via une file/after-callback.
- app.py : point d’entrée, chargement des ressources (icône), démarrage UI.

3) Flux de données (happy path)
- Au démarrage : charger config → vérifier cookie → si absent, afficher “Configurer le cookie”.
- Si cookie présent :
  1) GET /api/organizations → sélectionner la première org (ou celle mémorisée).
  2) GET /api/organizations/{org}/stats → extraire message_limit.*.
  3) GET /api/organizations/{org}/billing/(subscription|usage) → extraire plan, extra_usage, credits.balance.
  4) Calculs → maj UI (pourcentages, restants, reset local, couleurs).
- Timer : toutes les X minutes, re-lancer la séquence. Bouton Refresh force la même séquence.
- En cas d’erreur :
  - 401/403 → état “Re-login required”, suspendre l’auto-refresh.
  - 5xx/timeouts → afficher “Maintenance/N/A”, continuité UI, logs locaux sobres.

4) Modèles de données (pseudo)
- Organization { uuid: str, name?: str }
- MessageLimit { remaining?: int, quantity?: int, resets_at?: str }
- Stats { message_limit?: MessageLimit, weekly?: { used?: int, total?: int, resets_at?: str } }
- Billing { plan?: str, extra_usage?: { amount: float, currency: str, cap?: float }, credits?: { balance: float, currency: str } }

5) UI/UX (cartes)
- Carte A (Session Usage – 5h rolling window)
  - Titre, sous-titre, progress bar, % utilisé (texte), “X/Y messages” si dispo, “Resets HH:MM” (local).
- Carte B (Weekly)
  - Progress bar, % utilisé, “Resets <date/heure>” si dispo ; sinon “N/A”.
- Carte C (Billing)
  - “Extra usage: A / Cap” si dispo ; “Credits: B” si dispo.
  - Coloration basée sur % du cap si cap présent (sinon neutre).
- Footer
  - Settings (ouvre l’édition config/cookie), Refresh, Quit.

6) Contraintes non-fonctionnelles
- Performance : première réponse <2s si réseau OK ; UI jamais bloquée ; timeouts 3–5s ; backoff exponentiel.
- Résilience : schémas JSON variables tolérés (clés optionnelles), “N/A” propre, pas de crash.
- Sécurité/Confidentialité : ne jamais loguer le cookie ; stockage local protégé (droits fichiers) ; option coffre système pour secret ; aucun envoi de télémétrie.
- Accessibilité : tailles de police lisibles, focus clavier pour boutons clés.
- Localisation : formats de date/heure système ; devises affichées telles que reçues.
- Maintenance : logs locaux en rotation, niveaux INFO/WARN/ERROR ; code modulaire, testable.

7) Emballage et distribution
- Empaqueter en .exe avec ressources (icône).
- Stratégie de mise à jour manuelle (V1) ; auto-start Windows (V2 option).
- Document “Comment récupérer le cookie de session” (copier-coller depuis le navigateur), avec avertissement de sécurité.

research.md

Hypothèses & inconnues
- Endpoints “internes” susceptibles d’évoluer (chemins exacts, clés JSON).
- Disponibilité d’un indicateur hebdomadaire consolidé ; sinon calcul ou indisponible (N/A).
- Présence/format d’“extra usage” et “credits.balance” selon le type de compte.

Alternatives techniques
- Authentification : 
  - V1 : saisie manuelle du cookie de session (simple, rapide).
  - V2 : automatiser la récupération via navigateur → non retenu (risques sécurité/portabilité).
- Stockage secret :
  - Fichier local protégé (MVP) vs coffre d’identifiants Windows (idéal).
- UI :
  - Cartes sombres minimalistes (cohérence, lisibilité) vs surcouche plus lourde (inutile pour MVP).

Gestion des risques
- Changement d’API → Découpler fortement api/anthropic_client, tests de contrats (snapshot JSON), bascule N/A et message “Maintenance”.
- 401/403 → Suspendre auto-refresh, bannière “Re-login required”.
- Déconnexions réseau → retry limité + backoff ; ne pas spammer (respect IP/throttling).

Tests (idées)
- Tests unitaires : calculs (%/couleurs), parsing défensif (clés manquantes), conversion de temps local.
- Tests d’intégration : routes principales avec fixtures JSON.
- Tests UI : états (ok, N/A, auth_error), bouton Refresh, timer.

Observabilité
- Journaux locaux sobres, rotation, aucun secret, niveau configurable.