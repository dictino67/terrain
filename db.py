"""Accès à la base de données PostgreSQL (module partagé par app.py et calendrier.py)."""

import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

SCHEMA_JOUEUR = """
CREATE TABLE IF NOT EXISTS joueur (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    gsm VARCHAR(20),
    email VARCHAR(255),
    date_inscription TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

SCHEMA_CALENDRIER = """
CREATE TABLE IF NOT EXISTS calendrier (
    id SERIAL PRIMARY KEY,
    date_sunday DATE NOT NULL UNIQUE
)
"""

SCHEMA_PARTICIPATION = """
CREATE TABLE IF NOT EXISTS calendrier_joueur (
    calendrier_id INTEGER NOT NULL REFERENCES calendrier(id) ON DELETE CASCADE,
    joueur_id INTEGER NOT NULL REFERENCES joueur(id),
    poste SMALLINT NOT NULL CHECK (poste BETWEEN 1 AND 4),
    PRIMARY KEY (calendrier_id, poste),
    UNIQUE (calendrier_id, joueur_id)
)
"""

COLONNES_CALENDRIER = {"id", "date_sunday"}


def get_connection():
    """Ouvre une connexion PostgreSQL à partir de DATABASE_URL (.env)."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL manquant : créez un fichier .env (voir .env.example).")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Crée les tables si nécessaires.

    Si une table 'calendrier' vide existe avec un ancien schéma (colonnes
    incompatibles), elle est recréée. Si elle contient des données, la
    migration est refusée pour éviter toute perte.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_JOUEUR)

                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'calendrier'"
                )
                existantes = {row[0] for row in cur.fetchall()}
                if existantes and existantes != COLONNES_CALENDRIER:
                    cur.execute("SELECT COUNT(*) FROM calendrier")
                    if cur.fetchone()[0] > 0:
                        raise RuntimeError(
                            "La table 'calendrier' existe avec un ancien schéma et contient "
                            "des données : sauvegardez-la puis supprimez-la manuellement."
                        )
                    logger.warning("Ancien schéma 'calendrier' détecté (table vide) : recréation.")
                    cur.execute("DROP TABLE calendrier")
                cur.execute(SCHEMA_CALENDRIER)
                cur.execute(SCHEMA_PARTICIPATION)

                # Unicité de l'email au niveau base (ignorée si des doublons existent déjà)
                cur.execute("SAVEPOINT idx_email")
                try:
                    cur.execute(
                        "CREATE UNIQUE INDEX IF NOT EXISTS joueur_email_unique "
                        "ON joueur (lower(email))"
                    )
                except psycopg2.Error:
                    cur.execute("ROLLBACK TO SAVEPOINT idx_email")
                    logger.warning(
                        "Doublons d'email existants : index unique non créé "
                        "(le contrôle applicatif reste actif)."
                    )
        logger.info("Schéma base de données vérifié.")
    finally:
        conn.close()
