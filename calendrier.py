#!/usr/bin/env python3
"""Génération du calendrier des matchs pour la saison 2026-2027.

Règles métier :
- Période : tous les dimanches entre le 2026-10-01 et le 2027-03-30 inclus
  (si une borne n'est pas un dimanche, on prend le premier/dernier dimanche
  compris dans la période). Chaque match comporte exactement 4 joueurs
  (postes 1 à 4).
- Au moins 4 joueurs doivent être présents dans la table `joueur`,
  sinon la génération est bloquée avec une erreur claire.
- Équité : les joueurs tournent par combinaisons de 4 d'un dimanche à
  l'autre. À chaque match, on sélectionne les joueurs ayant le moins joué
  jusqu'ici (sélecteur glouton), de sorte que chaque joueur joue le même
  nombre de matchs pendant la saison. Si le nombre total de places
  (26 dimanches × 4) n'est pas divisible par le nombre de joueurs (ex. 5 ou
  6 joueurs), une égalité parfaite est impossible : la rotation la plus
  équitable est appliquée (écart max d'un match entre deux joueurs) et
  consignée dans les logs. Avec 4 joueurs, l'égalité est parfaite.
- Immuabilité : la génération ne s'exécute qu'une seule fois ; si le
  calendrier contient déjà des matchs, il faut passer force=True.

Utilisable en CLI (python calendrier.py [--force]) ou importé par l'API Flask
(fonction generer_calendrier).
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2

from db import get_connection, init_db

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Brussels")
SAISON_DEBUT = date(2026, 10, 1)
SAISON_FIN = date(2027, 3, 30)
JOUEURS_MINIMUM = 4
JOUEURS_PAR_MATCH = 4


class CalendrierError(Exception):
    """Erreur métier bloquant la génération du calendrier."""


def dimanches_saison(debut=SAISON_DEBUT, fin=SAISON_FIN):
    """Retourne la liste de tous les dimanches entre `debut` et `fin` inclus."""
    premier = debut + timedelta(days=(6 - debut.weekday()) % 7)
    dimanches = []
    courant = premier
    while courant <= fin:
        dimanches.append(courant)
        courant += timedelta(days=7)
    return dimanches


def composer_matchs(nb_dimanches, nb_joueurs):
    """Retourne, pour chaque dimanche, la liste des indices des 4 joueurs.

    Sélecteur glouton : à chaque dimanche, on prend les joueurs ayant le
    moins joué jusqu'ici (à nombre égal, ordre tournant), ce qui garantit
    un écart de participation d'au plus un match entre deux joueurs.
    Les postes 1 à 4 sont également décalés chaque semaine.
    """
    participations = [0] * nb_joueurs
    matchs = []
    for semaine in range(nb_dimanches):
        ordre = sorted(
            range(nb_joueurs),
            key=lambda j: (participations[j], (j - semaine) % nb_joueurs),
        )
        selection = sorted(ordre[:JOUEURS_PAR_MATCH], key=lambda j: (j - semaine) % nb_joueurs)
        for j in selection:
            participations[j] += 1
        matchs.append(selection)
    return matchs


def generer_calendrier(force=False):
    """Peuple la table calendrier pour la saison. Retourne un résumé (dict).

    Lève CalendrierError si les conditions métier ne sont pas remplies.
    """
    init_db()
    logger.info("Génération demandée le %s", datetime.now(TZ).isoformat())

    dimanches = dimanches_saison()
    if not dimanches:
        raise CalendrierError("Aucun dimanche trouvé dans la période de saison.")

    conn = get_connection()
    try:
        with conn:  # une seule transaction : tout ou rien
            with conn.cursor() as cur:
                cur.execute("SELECT id, nom, prenom FROM joueur ORDER BY id")
                joueurs = cur.fetchall()
                if len(joueurs) < JOUEURS_MINIMUM:
                    raise CalendrierError(
                        f"Au moins {JOUEURS_MINIMUM} joueurs requis "
                        f"({len(joueurs)} présent(s))."
                    )

                total_places = len(dimanches) * JOUEURS_PAR_MATCH
                par_joueur, reste = divmod(total_places, len(joueurs))
                if reste:
                    logger.warning(
                        "Équité parfaite impossible : %d places pour %d joueurs "
                        "(%d matchs × %d postes). Rotation la plus équitable : "
                        "%d joueur(s) joueront %d matchs, les autres %d.",
                        total_places, len(joueurs), len(dimanches), JOUEURS_PAR_MATCH,
                        reste, par_joueur + 1, par_joueur,
                    )

                cur.execute("SELECT COUNT(*) FROM calendrier")
                existants = cur.fetchone()[0]
                if existants and not force:
                    raise CalendrierError(
                        f"Calendrier déjà généré ({existants} matchs) : la génération "
                        "ne s'exécute qu'une fois par saison. Utilisez la "
                        "réinitialisation pour le régénérer."
                    )
                if existants:
                    cur.execute("DELETE FROM calendrier")
                    cur.execute("UPDATE joueur SET compteur = 0")
                    logger.info("Réinitialisation : %d matchs existants supprimés.", existants)

                ids = [j[0] for j in joueurs]
                for dimanche, indices in zip(dimanches, composer_matchs(len(dimanches), len(joueurs))):
                    cur.execute(
                        "INSERT INTO calendrier (date_sunday) VALUES (%s) RETURNING id",
                        (dimanche,),
                    )
                    match_id = cur.fetchone()[0]
                    cur.executemany(
                        "INSERT INTO calendrier_joueur (calendrier_id, joueur_id, poste) "
                        "VALUES (%s, %s, %s)",
                        [(match_id, ids[indice], poste) for poste, indice in enumerate(indices, start=1)],
                    )
                    cur.executemany(
                        "UPDATE joueur SET compteur = compteur + 1 WHERE id = %s",
                        [(ids[indice],) for indice in indices],
                    )
                    logger.info(
                        "Match créé pour le %s : %s",
                        dimanche.isoformat(),
                        ", ".join(f"{joueurs[i][1]} {joueurs[i][2]}" for i in indices),
                    )
    except psycopg2.Error as e:
        raise CalendrierError(f"Erreur base de données : {e}") from e
    finally:
        conn.close()

    resume = {
        "matchs_crees": len(dimanches),
        "joueurs": [f"{nom} {prenom}" for (_, nom, prenom) in joueurs],
        "matchs_par_joueur": par_joueur if not reste else f"{par_joueur} ou {par_joueur + 1}",
        "premier_match": dimanches[0].isoformat(),
        "dernier_match": dimanches[-1].isoformat(),
        "reinitialise": existants > 0,
    }
    logger.info(
        "Génération terminée : %d matchs pour %d joueurs (%s matchs chacun), du %s au %s.",
        resume["matchs_crees"], len(resume["joueurs"]), resume["matchs_par_joueur"],
        resume["premier_match"], resume["dernier_match"],
    )
    return resume


def main():
    parser = argparse.ArgumentParser(
        description="Génère le calendrier des matchs de la saison 2026-2027."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Réinitialise le calendrier existant avant de régénérer.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        resume = generer_calendrier(force=args.force)
    except (CalendrierError, RuntimeError) as e:
        logger.error(str(e))
        print(f"Erreur : {e}", file=sys.stderr)
        return 1

    print(f"Généré {resume['matchs_crees']} matchs pour {len(resume['joueurs'])} joueurs")
    print(f"Joueurs : {', '.join(resume['joueurs'])}")
    print(f"Matchs par joueur : {resume['matchs_par_joueur']}")
    print(f"Période : du {resume['premier_match']} au {resume['dernier_match']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
