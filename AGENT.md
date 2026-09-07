# AGENT.md

## Rôle de l'Agent

Cet agent est responsable du développement, de la maintenance et de l'évolution de l'application de gestion de calendrier de matchs de football. Il doit respecter scrupuleusement les spécifications techniques et les règles métier définies.

## Spécifications du Projet

### 1. Objectif Principal
Développer une application web complète (Frontend HTML/JS + Backend Flask + Base de données PostgreSQL) permettant de gérer des joueurs et de générer automatiquement un calendrier de matchs pour une saison sportive sur des dimanches précis.

### 2. Stack Technique
- **Frontend** : HTML5, JavaScript (Vanilla), Tailwind CSS (via CDN).
- **Backend** : Python (Flask), Python-dotenv (gestion des variables d'environnement).
- **Base de données** : PostgreSQL (via psycopg2).
- **Logique de génération** : Script Python dédié (`calendrier.py`) utilisant `datetime` ou `dateutil`.
- **Conteneurisation** : Docker.

### 3. Règles Métier Critiques
- **Règle des joueurs** : La génération est bloquée si **moins de 4 joueurs** sont présents en base. Chaque dimanche comporte **exactement 4 joueurs** ; au-delà de 4 joueurs, ils **tournent par combinaisons de 4** (round-robin, fenêtre glissante) pour jouer le même nombre de matchs. La saison comptant 26 dimanches (104 places), l'égalité est parfaite uniquement si le nombre de joueurs divise 104 (4, 8, 13…) ; sinon rotation la plus équitable (écart max 1 match, consigné dans les logs).
- **Modification** : chaque match peut être modifié individuellement (popup, 4 joueurs distincts existants). Avertissement affiché : une modification manuelle peut rompre l'équité.
- **Période de la Saison** : Plage du **2026-10-01** au **2027-03-30** (inclus). Seuls les dimanches sont pris en compte.
- **Intégrité des données** : Pas de doublons de matchs pour une même date. Utilisation systématique des IDs (clés étrangères) pour les relations joueurs/matchs. Validation stricte des formats (GSM international, Email unique).

### 4. Structure de la Base de Données (n8n_db)
- **Table `joueur`** : `id` (PK), `nom`, `prenom`, `gsm`, `email`.
- **Table `calendrier`** : `id` (PK), `date_sunday` (unique).
- **Table `calendrier_joueur`** : (`calendrier_id` FK vers `calendrier` ON DELETE CASCADE, `joueur_id` FK vers `joueur`, `poste` 1..4) — PK (calendrier_id, poste), UNIQUE (calendrier_id, joueur_id).

### 5. Instructions de Développement
#### Sécurité & Bonnes Pratiques
- **Injections SQL** : Utiliser impérativement des requêtes paramétrées.
- **Secrets** : Ne jamais coder en dur les credentials. Utiliser le fichier `.env`.
- **Validation** : Valider les données côté Frontend (UX) ET côté Backend (Sécurité).

#### Workflow de Test
1. Vérifier la connexion à la DB via l'URL dans `.env`.
2. Tester l'ajout d'un joueur via `ajout.html`.
3. Tenter de générer le calendrier avec < 4 joueurs (doit échouer).
4. Ajouter les joueurs manquants pour atteindre 4.
5. Lancer la génération et vérifier l'affichage sur `index.html`.

## Historique des Modifications
- **Initialisation** : Création du document de référence.
- **2026-09-07** : Réécriture complète de l'application.
  - `app.py` : suppression du code dupliqué et du serveur `http.server` parasite ; API sous `/api/*` ; pages servies par Flask sur le port 3020 ; validation backend complète (GSM belge normalisé en +32xxxxxxxxx, email unique insensible à la casse → 409) ; suppression d'un joueur utilisé au calendrier refusée (409).
  - `calendrier.py` : exige **exactement** 4 joueurs ; une seule transaction ; refuse de régénérer sans `--force` ; rotation des postes 1→4 chaque semaine ; code de sortie non nul en cas d'erreur ; journalise le cas « nombre de dimanches non divisible par 4 » (sans impact : chacun joue 100 % des matchs).
  - `db.py` (nouveau) : connexion + création des tables ; recrée `calendrier` si ancien schéma **vide** (colonnes `date`/`joueurN` varchar → `date_sunday` + FK `joueurN_id`).
  - `index.html` : vraie vue calendrier (date en français, joueurs via jointures), boutons « Créer calendrier » (avec proposition de régénération forcée si existant) et « Réinitialiser ».
  - `ajout.html` : affichage des erreurs backend (email dupliqué, etc.), badge « X / 4 joueurs », GSM flexible (0475…, +32…).
  - Ajout `.gitignore` (protège `.env`), `.env.example`, `.dockerignore` ; `Dockerfile` : copie explicite des fichiers (pas de secrets dans l'image), port 3020 cohérent.
- **2026-09-07 (suite)** : Modification manuelle d'un match, **puis annulée** par la règle d'immuabilité ci-dessous.
- **2026-09-07 (v3)** : Nouvelle règle « min. 4 joueurs, tout le monde joue chaque dimanche » + immuabilité.
  - Schéma : `calendrier(id, date_sunday)` + `calendrier_joueur(calendrier_id, joueur_id)` (remplace les 4 colonnes `joueurN_id`).
  - `calendrier.py` : plus d'erreur si > 4 joueurs ; chaque dimanche est créé avec TOUS les joueurs présents ; erreur « Au moins 4 joueurs requis » conservée.
  - `app.py` : endpoint `PUT /api/calendrier/<id>` supprimé (calendrier non modifiable après création) ; `GET /api/calendrier` renvoie `joueurs` (liste des noms).
  - `index.html` : colonne « Joueurs présents » ; popup et boutons Modifier supprimés ; « Créer calendrier » masqué dès que le calendrier existe, « Réinitialiser » affiché uniquement s'il existe.
  - `ajout.html` : badge « X (min. 4) », vert dès 4 joueurs.
- **2026-09-07 (v4)** : Retour à 4 joueurs par match + rotation + modification.
  - `calendrier_joueur` gagne la colonne `poste` (1..4) ; chaque match a exactement 4 joueurs.
  - `calendrier.py` : round-robin (fenêtre glissante de 4) ; log d'avertissement si l'équité parfaite est impossible (26×4 non divisible par le nombre de joueurs).
  - `app.py` : `PUT /api/calendrier/<id>` réintroduit (met à jour les 4 lignes de participation) ; `GET /api/calendrier` renvoie les 4 postes.
  - `index.html` : 4 colonnes Joueur 1-4 + bouton « Modifier » par match (popup, 4 selects depuis la table joueur) ; boutons « Créer calendrier »/« Réinitialiser » toujours visibles (la régénération forcée est proposée si le calendrier existe).
- **2026-09-07 (v5)** : Séparation consultation / administration.
  - `index.html` : vue **consultation** — boutons « Créer calendrier » et « Réinitialiser » retirés (le tableau et le bouton « Modifier » par match restent).
  - `indexnew.html` : nouvelle page **administration** (route `/indexnew.html`), identique mais avec les boutons « Créer calendrier » et « Réinitialiser ». Lien « Administration » ajouté dans sa barre de navigation.
- **2026-09-08** : Sécurisation de l'application et ajout de l'authentification.
  - Ajout de `login.html` (page de connexion Tailwind CSS avec logo tennis et messages d'erreur).
  - Gestion des variables d'environnement dans `.env` : `AUTH_USERNAME` (`joueur`), `AUTH_PASSWORD` (`Hiver@1610`) et `SECRET_KEY`.
  - Protection des routes dans `app.py` via `before_request` et sessions Flask (`/login`, `/logout`, `/api/login`, `/api/logout`).
  - Ajout du bouton Déconnexion dans les barres de navigation (`index.html`, `indexnew.html`, `ajout.html`).
  - Mise à jour du `Dockerfile` pour inclure `login.html`.