# Instructions pour les assistants IA (Copilot, etc.)

Tu es un assistant de développement travaillant sur ce dépôt. Suis scrupuleusement
ces consignes et les règles métier ci-dessous. Le document de référence complet
est `AGENT.md` à la racine.

## Contexte du projet

Application web de gestion de calendrier de matchs de tennis (saison hivernale,
matchs le dimanche). Voir `README.md` pour l'installation et le démarrage.

- **Backend** : Python + Flask (`app.py`), API REST sous `/api/*`, port **3020**.
- **Génération du calendrier** : `calendrier.py` (importable et utilisable en CLI
  avec `--force`).
- **Base de données** : PostgreSQL via `psycopg2`, accès centralisé dans `db.py`
  (`get_connection()`, `init_db()`).
- **Frontend** : HTML + JavaScript vanilla + Tailwind CSS (via CDN), pages servies
  par Flask : `login.html`, `index.html` (consultation), `indexnew.html`
  (administration), `ajout.html` (gestion des joueurs).
- **Conteneurisation** : `Dockerfile` + `docker-compose.yml` (service `web`,
  conteneur `terrain_web`, image `terrain_web:latest`).

## Règles métier à ne jamais casser

- **Authentification** : toutes les routes sont protégées par session Flask
  (`before_request`), sauf `/login*`, `/api/login` et `/tennis.png`.
  Identifiants dans `.env` (`AUTH_USERNAME`, `AUTH_PASSWORD`, `SECRET_KEY`).
- **Joueurs** : min. 4 joueurs en base pour générer un calendrier. Champs validés
  côté client **et** serveur (GSM belge normalisé en `+32xxxxxxxxx`, email unique
  insensible à la casse). Le compteur de matchs joués (`joueur.compteur`) est
  **automatique** : +1/-1 lors de la modification d'un match, remise à zéro à la
  réinitialisation du calendrier — il n'est pas modifiable via l'API.
- **Matchs** : exactement **4 joueurs distincts** par match (postes 1 à 4).
  Période : dimanches entre le 2026-10-01 et le 2027-03-30 inclus.
- **Génération** : rotation round-robin la plus équitable possible (écart max
  d'un match entre joueurs). Une seule génération par saison sauf
  `force`/`--force` (qui vide d'abord le calendrier). Une seule transaction :
  tout ou rien.
- **Suppression de joueur** : refusée (409) si le joueur est utilisé dans le
  calendrier.
- **Exports calendrier** : sur `index.html`, chaque date propose un lien Google
  Calendar (événement pré-rempli) et un téléchargement `.ics` via
  `GET /api/calendrier/<id>/ics` (événement journée entière ; 404 si le match
  est passé).

## Conventions de code

- **Langue** : interface, messages d'erreur et commentaires en **français**.
- **SQL** : requêtes paramétrées (`%s`) uniquement — jamais de concaténation.
  Une transaction (`with conn:`) par opération ; toujours fermer la connexion
  (`try/finally: conn.close()`).
- **API** : réponses JSON ; erreurs métier en 4xx avec `{"error": "..."}`,
  erreurs DB/serveur en 500. Codes dédiés : 409 (conflit : email dupliqué,
  calendrier existant, joueur utilisé), 404 (introuvable), 400 (validation).
- **Frontend** : fonctions JS nommées en français, affichage des erreurs backend
  dans `#message`. Échapper tout HTML injecté (`echapperHtml`). Dates affichées
  via `Intl.DateTimeFormat('fr-BE', ...)`.
- **Secrets** : jamais en dur — toujours via `.env` (modèle : `.env.example`).
  Le `.env` ne doit jamais être commité (protégé par `.gitignore`).

## Workflow attendu

1. Lire `AGENT.md` (historique et règles détaillées) avant toute évolution.
2. Changer les dépendances uniquement via `requirements.txt`.
3. Valider la syntaxe Python (`python3 -m py_compile app.py calendrier.py db.py`)
   et relire les pages HTML modifiées avant de conclure.
4. Pour déployer : `docker compose build && docker compose up -d`, puis vérifier
   `docker compose ps`, `docker logs terrain_web` et un appel HTTP sur
   `http://localhost:3020/`.
5. Mettre à jour `AGENT.md` (section « Historique des Modifications ») et
   `README.md` quand le comportement change.

## À ne pas faire

- Ne pas contourner l'authentification ni ajouter de routes publiques sans
  demande explicite.
- Ne pas modifier le schéma PostgreSQL sans migration sûre (voir `init_db()`).
- Ne pas réintroduire la modification manuelle du compteur de matchs joués.
- Ne pas générer de contenu copié sous copyright.
