1. Initialiser le dépôt (licence, README, .gitignore). Définir structure src/ et dossiers ui/, api/, core/, domain/.
2. Créer schema de config (JSON) avec valeurs par défaut (intervalle=5min, org_uuid=null). Charger/valider/écrire.
3. Implémenter abstraction de stockage du cookie (MVP: fichier de config chiffré/base64 + avertissement ; prévoir interface pour coffre système en V2).
4. Écrire client HTTP générique avec session, en-têtes, timeouts, retry/backoff (max 2–3), gestion 401/403/5xx.
5. Implémenter api/anthropic_client :
   - get_organizations() → uuid.
   - get_stats(org) → message_limit{remaining, quantity, resets_at?}.
   - get_billing(org) → plan, extra_usage?, credits?.
   - Parsing défensif (.get), gestion d’erreurs, types optionnels.
6. Écrire domain/calculations :
   - compute_percent(remaining, quantity) + garde-fous (division par zéro).
   - estimate_remaining() si “remaining” manquant.
   - color_bucket(percent) → safe/warning/critical.
   - to_local_time(iso_ts) → string locale.
7. Prototyper l’UI : fenêtre 360×550, fond sombre, 3 cartes vides + footer (Settings/Refresh/Quit). Intégrer icône.
8. Relier UI↔controller : afficher états initiaux (“Configurer cookie” si absent).
9. Ajouter thread de rafraîchissement :
   - Cycle : org → stats → billing → calculs → mise à jour UI.
   - Timer auto selon config ; bouton Refresh force un cycle unique.
10. Implémenter cartes :
    - Carte Session : progress bar, %, X/Y, “Resets HH:MM”.
    - Carte Weekly : progress bar + reset si dispo, sinon “N/A”.
    - Carte Billing : “Extra usage A/Cap” et “Credits B” si dispo (sinon masquer/“N/A”).
11. Gérer erreurs/alertes :
    - 401/403 → bannière “Re-login required”, désactiver auto-refresh.
    - 5xx/timeouts → “Maintenance/N/A”, conserver dernière valeur connue si pertinente.
12. Appliquer code couleur (#6FD771, #F0A24C, #EB564F) selon percent/cap. Vérifier contraste/fond.
13. Tests unitaires (calculs, parsing, conversion horaires) + tests d’intégration (fixtures JSON).
14. Journalisation locale (rotation, sans secrets). Niveau via config.
15. Emballer en .exe avec ressources (icône). Vérifier exécution sur Windows propre (sans Python installé).
16. Rédiger guide utilisateur :
    - Récupération/placement du cookie.
    - Signification des états/couleurs.
    - Dépannage (401/403, N/A).
17. QA finale : mesurer temps d’affichage initial (<2s), stabilité (1h de polling), pas de gels UI.
18. (Option V2) Intégrer coffre Windows pour le cookie, auto-start optionnel, sélecteur d’organisation, mise à jour in-app.
