# Architecture - Terrain

## 🏗️ Vue d'ensemble

```
┌─────────────────────────────────────────┐
│         Frontend (HTML/JS)              │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ login    │ │ index    │ │ ajout   │ │
│  │ .html    │ │ .html    │ │ .html   │ │
│  └──────────┘ └──────────┘ └─────────┘ │
│         (Tailwind CSS via CDN)          │
└───────────────┬─────────────────────────┘
                │ HTTPS / Port 3020
                ▼
        ┌─────────────────┐
        │   Backend       │
        │   Flask         │
        │   (app.py)      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  PostgreSQL     │
        │  - joueur       │
        │  - calendrier   │
        └─────────────────┘
```

## 📦 Composants Principaux

| Composant | Fichier | Rôle |
|-----------|---------|------|
| **Frontend** | `login.html` | Authentification utilisateur |
| **Frontend** | `index.html` | Vue calendrier (consultation, liens Google/.ics) |
| **Frontend** | `indexnew.html` | Administration (créer/réinitialiser) |
| **Frontend** | `ajout.html` | CRUD joueurs |
| **Backend** | `app.py` | API REST + serveur web |
| **Backend** | `calendrier.py` | Script de génération des matchs |
| **Base** | PostgreSQL | Persistance données |

## 🔄 Flux d'Utilisation

1. **Authentification** → Connexion via `/login`
2. **Gestion joueurs** → Ajouter/modifier/supprimer (min. 4 joueurs requis)
3. **Génération calendrier** → Création automatique (dimanches 01/10/2026 - 30/03/2027)
4. **Consultation** → Vue interactive avec intégration Google Calendar + .ics

## 🌐 API REST Principale

```
POST   /api/login                        # Connexion
GET    /api/joueurs                      # Liste joueurs
POST   /api/calendrier/generer           # Générer calendrier
GET    /api/calendrier/:id/ics           # Export .ics par match
POST   /api/calendrier/reinitialiser     # Vider le calendrier
```

## ⚙️ Configuration Requise

- `DATABASE_URL` : Connexion PostgreSQL
- `AUTH_USERNAME` / `AUTH_PASSWORD` : Credentials d'authentification
- `SECRET_KEY` : Clé secrète Flask