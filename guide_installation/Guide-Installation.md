# Guide d'installation — Claude Win Monitor v1.8.4

**Claude Win Monitor** est un moniteur de quotas Claude en temps réel pour Windows.
Il affiche votre consommation de session (5h), hebdomadaire (7 jours) et votre budget mensuel.

---

## 1. Prérequis

Avant de commencer, vérifiez que votre ordinateur dispose de :

- **Windows 10 ou Windows 11** (64 bits)
- **Google Chrome** installé
- Un compte **Claude.ai** actif (abonnement Pro ou Team)

Aucune installation de Python ou d'autre logiciel n'est nécessaire.

---

## 2. Contenu de l'archive

L'archive `Claude-Win-Monitor-v1.8.4.zip` contient trois dossiers :

```
1-Installateur/
    Claude-Win-Monitor-Setup.exe   ← programme d'installation

2-Extension-Chrome/
    manifest.json
    background.js
    icon.png                       ← extension navigateur

3-Documentation/
    Guide-Installation.pdf         ← ce guide
    00-LISEZ-MOI.txt
```

---

## 3. Avant d'installer — antivirus

L'application est compilée en binaire natif Windows. Certains antivirus peuvent
réagir à l'installation d'un logiciel qu'ils ne connaissent pas encore.

**Le fichier d'installation est sûr : 0 détection sur 71 moteurs antivirus.**
Vérification indépendante : https://www.virustotal.com/gui/file/37ee2d1c23e8b1514540e28a50d99416b6fa060807907cbec77a624f22f88f9f/

Si vous utilisez **ESET Internet Security** :
1. Faites un clic droit sur l'icône ESET dans la barre des tâches
2. Sélectionnez **Suspendre la protection** → choisir une durée (10 minutes suffisent)
3. Procédez à l'installation
4. Réactivez la protection et ajoutez une exclusion sur le dossier d'installation
   (voir section 5)

---

## 4. Installation

### 4.1 Lancer l'installateur

Double-cliquez sur `1-Installateur\Claude-Win-Monitor-Setup.exe`.

### 4.2 Alerte SmartScreen (si elle apparaît)

Windows peut afficher un écran bleu intitulé **"Windows a protégé votre ordinateur"**.

> Cette alerte s'affiche pour tout logiciel nouvellement publié, quelle que soit
> son origine. Elle disparaîtra au fur et à mesure que le logiciel gagnera
> en réputation.

Pour continuer :

1. Cliquez sur **Informations complémentaires**
2. Cliquez sur **Exécuter quand même**

*[IMAGE — capture de l'écran SmartScreen]*

### 4.3 Étapes de l'assistant d'installation

**Étape 1 — Dossier de destination**

Le dossier d'installation proposé par défaut est :
`C:\Program Files (x86)\Claude-Win-Monitor`

Cliquez sur **Suivant** (vous pouvez conserver le dossier par défaut).

![Dossier de destination](install01.png)

---

**Étape 2 — Dossier du menu Démarrer**

L'assistant propose de créer un raccourci dans le menu Démarrer
sous le nom **Claude Win Monitor**.

Cliquez sur **Suivant**.

![Menu Démarrer](install02.png)

---

**Étape 3 — Prêt à installer**

Un récapitulatif s'affiche avec le dossier de destination
et le dossier du menu Démarrer choisis.

Cliquez sur **Installer**.

![Prêt à installer](install03.png)

---

**Étape 4 — Fin de l'installation**

L'installation est terminée. La case **Lancer Claude Win Monitor** est cochée
par défaut — l'application démarrera automatiquement après avoir cliqué sur
**Terminer**.

Cliquez sur **Terminer**.

![Fin de l'installation](install04.png)

---

## 5. Après l'installation — exclusion antivirus

Si vous avez suspendu votre antivirus à l'étape 3, réactivez-le maintenant
et ajoutez une exclusion permanente sur le dossier d'installation.

**Pour ESET Internet Security :**
1. Ouvrez ESET → **Configuration** → **Exclusions**
2. Cliquez sur **Ajouter** → **Dossier**
3. Sélectionnez `C:\Program Files (x86)\Claude-Win-Monitor`
4. Validez

*[IMAGE — capture de l'exclusion ESET]*

**Pour Windows Defender :**
1. Ouvrez **Sécurité Windows** → **Protection contre les virus et menaces**
2. **Gérer les paramètres** → **Ajouter ou supprimer des exclusions**
3. **Ajouter une exclusion** → **Dossier**
4. Sélectionnez `C:\Program Files (x86)\Claude-Win-Monitor`

---

## 6. Installation de l'extension Chrome

L'extension Chrome envoie automatiquement votre clé de session à l'application.
Sans elle, vous devrez saisir la clé manuellement.

### 6.1 Ouvrir la page des extensions

Dans Chrome, tapez dans la barre d'adresse :
```
chrome://extensions
```
et appuyez sur **Entrée**.

*[IMAGE — barre d'adresse Chrome avec chrome://extensions]*

### 6.2 Activer le mode développeur

En haut à droite de la page, activez le bouton **Mode développeur**.

*[IMAGE — bouton Mode développeur]*

### 6.3 Charger l'extension

1. Cliquez sur **Charger l'extension non empaquetée**
2. Dans la fenêtre qui s'ouvre, naviguez jusqu'à l'archive dézippée
3. Sélectionnez le dossier **`2-Extension-Chrome`**
4. Cliquez sur **Sélectionner un dossier**

L'extension **Claude Win Monitor** apparaît dans la liste.

*[IMAGE — extension chargée dans Chrome]*

### 6.4 Alerte périodique Chrome

Chrome affiche régulièrement un bandeau :
> *"Désactivez les extensions de développeur pour votre sécurité"*

Cliquez simplement sur **Ignorer** ou **Ne plus afficher**. L'extension
continuera de fonctionner normalement.

*[IMAGE — bandeau Chrome extensions développeur]*

---

## 7. Premier lancement

### 7.1 Ce que vous voyez au démarrage

Au premier lancement, l'application s'ouvre et affiche un message vous invitant
à configurer votre clé de session.

*[IMAGE — fenêtre principale au premier lancement]*

### 7.2 Connexion automatique

Si l'extension Chrome est installée et que vous êtes connecté à **claude.ai**
dans Chrome, la connexion s'effectue **automatiquement** en quelques secondes.

L'application affiche alors vos quotas en temps réel :
- **Session** — consommation sur les 5 dernières heures
- **Hebdomadaire** — consommation sur les 7 derniers jours
- **Budget** — consommation mensuelle

*[IMAGE — fenêtre principale avec les quotas affichés]*

### 7.3 Connexion manuelle (si nécessaire)

Si la connexion automatique ne fonctionne pas :

1. Cliquez sur l'icône **Paramètres** ⚙ (barre du bas)
2. Suivez les instructions pour récupérer votre clé de session manuellement
   depuis les outils de développement de Chrome (F12)

---

## 8. Icône dans la barre des tâches (tray)

Claude Win Monitor s'exécute en arrière-plan avec une icône dans la zone
de notification (coin inférieur droit de l'écran).

Un clic droit sur l'icône permet de :
- **Afficher** — ramener la fenêtre au premier plan
- **Actualiser** — forcer une mise à jour des quotas
- **Quitter** — fermer l'application

*[IMAGE — menu contextuel tray]*

---

## 9. Mise à jour

Pour mettre à jour l'application :

1. Téléchargez la nouvelle version de l'archive ZIP
2. Lancez le nouveau `Claude-Win-Monitor-Setup.exe`
3. Cliquez sur **Suivant** → **Installer** → **Terminer**

**Votre configuration est automatiquement conservée** — la clé de session
et les paramètres sont stockés dans un dossier séparé qui n'est jamais
touché par l'installateur.

---

## 10. Désinstallation

1. Ouvrez **Paramètres Windows** → **Applications** → **Applications installées**
2. Recherchez **Claude Win Monitor**
3. Cliquez sur **⋯** → **Désinstaller**

Votre configuration (clé de session) est conservée dans :
`C:\Users\[votre nom]\AppData\Local\Claude-Win-Monitor\`

Vous pouvez supprimer ce dossier manuellement si vous souhaitez
une désinstallation complète.

---

## Assistance

Code source et signalement de problèmes :
https://github.com/M0DR1SH/Claude-Win-Monitor

---

*Claude Win Monitor v1.8.4 — Laurent Gérard — 2026*
