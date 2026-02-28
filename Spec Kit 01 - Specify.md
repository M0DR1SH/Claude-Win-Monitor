Nom: Claude-Win-Monitor

Objectif produit
- Offrir aux utilisateurs Windows une app native, discrète (philosophie “set & forget”), pour visualiser en un coup d’œil l’état de leurs quotas Claude (fenêtre glissante 5h, hebdo) et des informations de facturation/crédits, sans ouvrir le navigateur.

Utilisateurs cibles
- Utilisateurs de claude.ai (web) sur Windows souhaitant suivre leurs limites d’usage en temps réel.
- Utilisateurs avec abonnement (Pro/Teams/Enterprise) et/ou crédits API, ayant besoin d’un suivi budgétaire simple.

Valeur / bénéfices
- Anticiper le blocage de quota (couleurs + horodatage du prochain reset).
- Réduire les allers-retours vers le site.
- Comprendre l’usage hebdomadaire et (si disponible) la dépense ou les crédits restants.

Authentification (état v1.7.2)
- Méthode principale : extension navigateur Chrome/Edge (dossier extension/)
  → lit automatiquement le cookie sessionKey via chrome.cookies.get()
  → envoie à l'app via POST localhost:27182 (receiver HTTP intégré)
  → zéro intervention utilisateur après installation de l'extension
- Fallback : saisie manuelle dans la fenêtre Paramètres (inchangée)
- Token CLI Claude Code (sk-ant-oat01-) : écarté — solde prépayé inaccessible (403 claude.ai depuis jan 2026)
- Lecture directe cookies Chrome : abandonnée — nécessite droits admin Windows

Périmètre fonctionnel (MVP)
- Carte “Session Usage – 5h rolling window” :
  - Afficher % d’utilisation, messages restants/quantité totale si disponible, et l’heure locale du prochain reset.
  - Code couleur : <50% vert, 50–80% jaune, >80% rouge.
- Carte “Weekly usage” :
  - Afficher la progression hebdomadaire et l’horodatage de remise à zéro hebdo si disponible (sinon N/A propre).
- Carte “Billing / Extra usage / Credits” :
  - Afficher montant consommé vs plafond (si disponible).
  - Afficher solde de crédits prépayés API (optionnel et clairement séparé).
- Rafraîchissement :
  - Auto toutes X minutes (par défaut 5, modifiable).
  - Bouton “Refresh” manuel.
- Paramètres :
  - Saisie/édition du jeton de session (cookie) via un écran/boîte de dialogue ou fichier de config local.
  - Intervalle de rafraîchissement configurable.
- Résilience & UX :
  - Si données indisponibles/changent : afficher “N/A” ou “Maintenance” au lieu de crasher.
  - Si session expirée/invalidée : badge/état d’alerte “Re-login required” et arrêt du rafraîchissement auto.

Règles & comportements
- Conversion des timestamps reçus en heure locale du PC.
- Estimation des messages restants si seule la quantité/max est connue.
- Aucun appel tant que le cookie n’est pas fourni (écran d’attente/paramètre).
- Fenêtre fixe (≈360×550) avec cartes superposées et mode sombre cohérent.

Données (E/S)
- Entrées : cookie de session utilisateur (texte), identifiant d’organisation, JSON de stats/usage/billing, intervalle de refresh.
- Sorties UI : % utilisé, messages restants/total, horodatage de reset (local), progression hebdo, montants (devise telle que renvoyée), états d’erreur/alerte.
- États persistés localement : cookie (ou poignée vers coffre système), préférences (intervalle, dernière org sélectionnée).

Contraintes fonctionnelles
- App strictement desktop (non-web), minimaliste, non intrusive, responsive au clic, jamais bloquante pendant les appels réseau.
- Affichage lisible en mode sombre (cartes, coins arrondis, typographie sans-serif).
- Pas d’authentification complète intégrée ; l’utilisateur fournit son cookie.

Hors-périmètre (V1)
- Pas d’envoi de messages à Claude.
- Pas d’OAuth complet.
- Pas de multi-comptes multi-orgs simultanés (sélection simple au besoin).
- Pas de Mac/Linux pour la première version.
- Pas de conversion de devise automatique (affichage brut si non spécifié).

Critères de succès (MVP)
- Lancer l’app, coller le cookie, voir en <2s des chiffres cohérents sur Session/Weekly/Billing (si dispo), couleurs correctes, prochain reset lisible, aucun gel UI, et gestion propre des erreurs (N/A/alertes).