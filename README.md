# Terrain — Calendrier de matchs (saison 2026-2027)

Application web simple pour gérer 4 joueurs et générer automatiquement le
calendrier des matchs de la saison : tous les dimanches entre le
**01/10/2026** et le **30/03/2027**.

- **Frontend** : `index.html` (vue calendrier, consultation), `indexnew.html` (même vue + boutons « Créer calendrier » / « Réinitialiser » — administration) et `ajout.html` (gestion des joueurs), Tailwind CSS via CDN, JavaScript vanilla.
- **Backend** : `app.py` (Flask) — sert les pages et l'API REST sur le port **3020**.
- **Génération** : `calendrier.py` — peuple la table `calendrier` (utilisable en CLI ou via l'API).
- **Base** : PostgreSQL (tables `joueur` et `calendrier`, créées automatiquement au démarrage).

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # puis renseigner DATABASE_URL
```

## Démarrage

```bash
python app.py
# puis ouvrir http://localhost:3020
```

En Docker :

```bash
docker build -t terrain .
docker run --rm -p 3020:3020 --env-file .env terrain
```

## Utilisation

1. Ouvrir **Gestion des joueurs** et ajouter/modifier/supprimer des joueurs
   (nom, prénom, GSM belge, email unique — validés côté client et serveur).
2. Avoir **au moins 4 joueurs** enregistrés (badge « X (min. 4) »).
3. Sur la page **Calendrier**, cliquer **Créer calendrier** : chaque dimanche
   reçoit **exactement 4 joueurs**, qui **tournent** d'une semaine à l'autre
   pour jouer le même nombre de matchs (avec 4 joueurs, tout le monde joue
   les 26 matchs ; avec plus, la répartition est la plus équitable possible).
4. Chaque match peut être **modifié** individuellement (bouton « Modifier »).
5. Le bouton **Réinitialiser** vide le calendrier (permet de régénérer).

## Génération en ligne de commande

```bash
python calendrier.py          # génère le calendrier (refuse s'il existe déjà)
python calendrier.py --force  # réinitialise puis régénère
```

## API REST

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/joueurs` | Liste des joueurs |
| POST | `/api/joueurs` | Ajouter un joueur |
| PUT | `/api/joueurs/<id>` | Modifier un joueur |
| DELETE | `/api/joueurs/<id>` | Supprimer (refusé si utilisé au calendrier) |
| GET | `/api/calendrier` | Liste des matchs (4 joueurs, postes 1 à 4) |
| PUT | `/api/calendrier/<id>` | Modifier les 4 joueurs d'un match (doivent être différents) |
| POST | `/api/calendrier/generer` | Générer (`{"force": true}` pour régénérer) |
| POST | `/api/calendrier/reinitialiser` | Vider le calendrier |
