# AGENT.md

---

## 🎯 Rôle de l'Agent

Cet agent est responsable du développement, de la maintenance et de l'évolution de l'application de gestion de calendrier de matchs de tennis. Il doit respecter scrupuleusement les spécifications techniques et les règles métier définies ci-dessous.

---

## 📋 Contexte du Projet

**Application web complète** permettant à un groupe de joueurs de gérer leur participation aux matchs d'une saison sportive. Le calendrier est généré automatiquement selon des règles d'équité strictes.

- **Saison** : 2026-2027 (Hiver)
- **Période active** : 1er octobre 2026 → 30 mars 2027
- **Fréquence des matchs** : Chaque dimanche
- **Nombre total de dimanches** : 26 matchs
- **Objectif** : Répartir équitablement les joueurs sur l'ensemble des matchs

---

## 🛠️ Stack Technique

| Composant | Technologie | Détails |
|-----------|-------------|---------|
| **Frontend** | HTML5, JavaScript Vanilla | Tailwind CSS via CDN (design responsive) |
| **Backend** | Python 3.11 + Flask | API REST sur `/api/*`, port 3020 |
| **Base de données** | PostgreSQL | Connexion via `DATABASE_URL` (.env) |
| **Dépendances** | Flask, psycopg2-binary, python-dotenv, python-dateutil | Voir `requirements.txt` |
| **Conteneurisation** | Docker | Image optimisée (secrets hors image) |

---

## 🗄️ Architecture de la Base de Données

### Schéma Relationnel

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐
│   joueur    │       │  calendrier  │       │ calendrier_joueur│
├─────────────┤       ├──────────────┤       ├──────────────────┤
│ id (PK)     │──┐    │ id (PK)      │◄──────│ calendrier_id(FK)│
│ nom         │  │    │ date_sunday  │       │ joueur_id(FK)    │
│ prenom      │  └────│              │       │ poste (1..4)     │
│ gsm         │       │              │       │                  │
│ email       │       └──────────────┘       └──────────────────┘
│ compteur    │               ▲                    │
│ date_insc.  │               │                    │
└─────────────┘               └────────────────────┘
      │                               (relation N à 4)
      └──→ UNIQUE INDEX ON LOWER(email)
```

### Définition des Tables

**Table `joueur`** :
- `id` (SERIAL, PK)
- `nom`, `prenom` (VARCHAR(100), NOT NULL)
- `gsm` (VARCHAR(20)) — format normalisé `+32xxxxxxxxx`
- `email` (VARCHAR(255)) — unique, insensible à la casse
- `date_inscription` (TIMESTAMP, default CURRENT_TIMESTAMP)
- `compteur` (INTEGER, default 0) — nombre de matchs joués

**Table `calendrier`** :
- `id` (SERIAL, PK)
- `date_sunday` (DATE, UNIQUE) — la date du dimanche

**Table `calendrier_joueur`** (table de liaison) :
- `calendrier_id` (FK → calendrier.id, ON DELETE CASCADE)
- `joueur_id` (FK → joueur.id)
- `poste` (SMALLINT, CHECK BETWEEN 1 AND 4)
- **PK composite** : (`calendrier_id`, `poste`)
- **UNIQUE** : (`calendrier_id`, `joueur_id`)

---

## 📜 Règles Métier Critiques

### 1. Nombre Minimum de Joueurs
⚠️ **Au moins 4 joueurs requis** pour générer le calendrier. Si moins de 4 joueurs sont présents, la génération échoue avec l'erreur : *"Au moins 4 joueurs requis."*

### 2. Composition des Matchs
- Chaque match comporte **exactement 4 joueurs** (postes 1 à 4).
- Les joueurs **tournent par combinaisons de 4** d'un dimanche à l'autre (algorithme glouton).
- **Équité garantie** : l'écart maximum entre deux joueurs est d'**au plus 1 match**.

### 3. Période de Saison
- Début : **2026-10-01** (premier dimanche)
- Fin : **2027-03-30** (dernier dimanche inclus)
- Nombre total de dimanches : **26 matchs**

### 4. Immuabilité du Calendrier
- La génération ne s'exécute **qu'une seule fois** par saison.
- Pour régénérer, il faut **réinitialiser** le calendrier (supprime tous les matchs et remet à zéro les compteurs).
- Option `--force` en CLI ou `{ "force": true }` via l'API pour régénérer sans passer manuellement par la réinitialisation.

### 5. Validation des Données
- **GSM** : formats acceptés → `+32475123456`, `0475123456`, `0032475123456` (avec/sans espaces, points, tirets)
- **Email** : doit être unique dans la base de données (insensible à la casse)
- **Nom & Prénom** : obligatoires, max 100 caractères

### 6. Modification des Matchs
- Un match peut être modifié individuellement via l'interface.
- Les 4 joueurs doivent être **distincts** et **existants** dans la table `joueur`.
- Une modification manuelle rompt potentiellement l'équité automatique.

---

## 🖥️ Fonctionnalités par Page

| Page | Route | Description | Actions Disponibles |
|------|-------|-------------|---------------------|
| **Login** | `/login`, `/login.html` | Authentification | Connexion, redirection vers page suivante |
| **Calendrier (Consultation)** | `/index.html` | Affiche le calendrier complet | Voir les matchs, modifier un match, exporter en Google Calendar / .ics |
| **Administration** | `/indexnew.html` | Vue admin avec contrôles | Créer calendrier, réinitialiser, modifier un match |
| **Gestion Joueurs** | `/ajout.html` | CRUD joueurs | Ajouter, modifier, supprimer des joueurs |



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