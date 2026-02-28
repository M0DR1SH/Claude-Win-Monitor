# Guide — Installation de l'extension & mise à jour de la sessionKey
### Claude-Win-Monitor | LG @ IA Mastery | 28/02/2026

---

## Principe

**Claude-Win-Monitor** a besoin d'une clé de session (`sessionKey`) pour
interroger l'API de Claude et afficher vos statistiques d'usage.

Cette clé est un cookie de votre navigateur, automatiquement géré par Claude.
L'extension **Claude Session Helper** la récupère et la transmet à l'application
sans aucune intervention de votre part.

---

## Prérequis

- Navigateur **Google Chrome** ou **Microsoft Edge**
- Être **connecté sur [claude.ai](https://claude.ai)** dans ce navigateur
- Application **Claude-Win-Monitor** installée

---

## Installation de l'extension (une seule fois)

### Étape 1 — Ouvrir le gestionnaire d'extensions

Dans Chrome ou Edge, cliquez sur le menu ⋮ (trois points) en haut à droite,
puis **Extensions → Gérer les extensions**.

Ou tapez directement dans la barre d'adresse :
```
chrome://extensions
```

![Ouvrir le gestionnaire d'extensions](extension01.png)

---

### Étape 2 — Activer le mode développeur

En haut à droite du gestionnaire d'extensions, activez le bouton
**Mode développeur**.

![Activer le mode développeur](extension02.png)

---

### Étape 3 — Charger l'extension

Cliquez sur **Charger l'extension non empaquetée**, puis naviguez jusqu'au
dossier `extension/` du projet Claude-Win-Monitor et sélectionnez-le.

L'extension **Claude Session Helper** apparaît dans la liste.

![Extension installée](extension03.png)

---

### Étape 4 — Vérification

1. Lancez **Claude-Win-Monitor** (`app.py`)
2. Dans les secondes qui suivent, l'application reçoit automatiquement
   la clé de session et affiche vos statistiques
3. La fenêtre **Paramètres** se ferme d'elle-même si elle s'était ouverte

> **L'extension peut ensuite être désactivée.** La clé est sauvegardée
> localement. L'app fonctionnera normalement jusqu'au prochain changement
> de session.

---

## Mise à jour de la sessionKey

La `sessionKey` expire ou change dans deux cas :
- **Déconnexion** depuis claude.ai puis reconnexion
- **Expiration naturelle** de la session (rare)

### Méthode automatique (recommandée)

1. **Réactiver** l'extension dans `chrome://extensions`
2. La clé est envoyée automatiquement à l'app en quelques secondes
3. Désactiver à nouveau l'extension

### Méthode manuelle (fallback)

Si l'extension n'est pas disponible :

1. Ouvrir **claude.ai** dans le navigateur
2. Appuyer sur **F12** pour ouvrir les DevTools
3. Aller dans **Application → Cookies → https://claude.ai**
4. Copier la valeur du cookie `sessionKey` (`sk-ant-sid02-...`)
5. Dans l'app, cliquer sur **⚙ Paramètres**
6. Coller la valeur et cliquer sur **Sauvegarder & Relancer**

---

## Fonctionnement de l'extension

L'extension s'active automatiquement dans les cas suivants :

| Événement | Action |
|---|---|
| Démarrage du navigateur | Envoi de la sessionKey |
| Installation / réactivation | Envoi immédiat |
| Chargement d'un onglet claude.ai | Envoi |
| Renouvellement du cookie par Claude | Envoi automatique |
| Démarrage de l'app (détecté en 10s) | Envoi si app absente au départ |

Si l'app n'est pas encore lancée, l'extension réessaie jusqu'à **10 fois**
toutes les **5 secondes**.

---

## Sécurité

- La `sessionKey` est transmise **uniquement en local** (`localhost:27182`)
- Elle est stockée dans `claude_monitor_config.json` sur votre machine
- L'extension ne communique avec **aucun serveur externe**
- Permissions demandées : `cookies` (lecture claude.ai) + `tabs` (détection page)

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| App reste vide après lancement | Extension désactivée | Réactiver l'extension |
| Fenêtre Paramètres reste ouverte | Extension n'a pas encore envoyé | Attendre 10s ou désactiver/réactiver |
| Erreur 403 dans l'app | SessionKey expirée | Réactiver l'extension (ou méthode manuelle) |
| Extension ne trouve pas de cookie | Non connecté sur claude.ai | Se connecter puis réactiver l'extension |
