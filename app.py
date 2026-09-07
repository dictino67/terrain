"""Backend Flask : sert les pages statiques et l'API REST (port 3020).

Endpoints API :
- GET    /api/joueurs                  Liste des joueurs
- POST   /api/joueurs                  Ajout d'un joueur (validation complète)
- PUT    /api/joueurs/<id>             Modification d'un joueur
- DELETE /api/joueurs/<id>             Suppression (refusée si utilisé au calendrier)
- GET    /api/calendrier               Liste des matchs (4 joueurs par match, postes 1 à 4)
- PUT    /api/calendrier/<id>          Modifie les 4 joueurs d'un match
- POST   /api/calendrier/generer       Génère le calendrier (une seule fois ; {"force": true} pour régénérer)
- POST   /api/calendrier/reinitialiser Vide le calendrier
"""

import logging
import os
import re

import psycopg2
from flask import Flask, jsonify, request, send_from_directory

from calendrier import CalendrierError, generer_calendrier
from db import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__, static_folder=None)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
GSM_RE = re.compile(r"^\+32[0-9]{9}$")


def normaliser_gsm(valeur):
    """Normalise un GSM belge vers le format international +32xxxxxxxxx.

    Accepte : +32475123456, 0032475123456, 0475123456, avec espaces,
    points, slashes ou tirets comme séparateurs.
    """
    compact = re.sub(r"[\s./-]", "", valeur or "")
    if compact.startswith("0032"):
        compact = "+" + compact[2:]
    elif compact.startswith("0"):
        compact = "+32" + compact[1:]
    return compact


def valider_joueur(data):
    """Valide les champs joueur. Retourne (erreurs: dict, valeurs normalisées: dict)."""
    erreurs = {}
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    gsm = normaliser_gsm(data.get("gsm"))
    email = (data.get("email") or "").strip().lower()

    if not nom:
        erreurs["nom"] = "Le nom est requis."
    elif len(nom) > 100:
        erreurs["nom"] = "Le nom est trop long (100 caractères max)."
    if not prenom:
        erreurs["prenom"] = "Le prénom est requis."
    elif len(prenom) > 100:
        erreurs["prenom"] = "Le prénom est trop long (100 caractères max)."
    if not GSM_RE.match(gsm):
        erreurs["gsm"] = "GSM invalide (formats acceptés : +32xxxxxxxxx ou 04xxxxxxxx)."
    if not EMAIL_RE.match(email):
        erreurs["email"] = "Email invalide."

    if erreurs:
        return erreurs, None
    return None, {"nom": nom, "prenom": prenom, "gsm": gsm, "email": email}


def email_existe(cur, email, exclure_id=None):
    """Vérifie l'unicité de l'email (insensible à la casse)."""
    if exclure_id is not None:
        cur.execute("SELECT 1 FROM joueur WHERE lower(email) = %s AND id <> %s", (email, exclure_id))
    else:
        cur.execute("SELECT 1 FROM joueur WHERE lower(email) = %s", (email,))
    return cur.fetchone() is not None


# ---------- Pages statiques ----------

@app.route("/")
def page_index():
    return send_from_directory(".", "index.html")


@app.route("/ajout.html")
def page_ajout():
    return send_from_directory(".", "ajout.html")


@app.route("/indexnew.html")
def page_indexnew():
    return send_from_directory(".", "indexnew.html")


@app.route("/tennis.png")
def image_fond():
    return send_from_directory(".", "tennis.png")


# ---------- API joueurs ----------

@app.route("/api/joueurs", methods=["GET"])
def lister_joueurs():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nom, prenom, gsm, email FROM joueur ORDER BY nom, prenom")
                rows = cur.fetchall()
        finally:
            conn.close()
        return jsonify([
            {"id": r[0], "nom": r[1], "prenom": r[2], "gsm": r[3], "email": r[4]}
            for r in rows
        ])
    except (psycopg2.Error, RuntimeError) as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


@app.route("/api/joueurs", methods=["POST"])
def ajouter_joueur():
    data = request.get_json(silent=True) or {}
    erreurs, valeurs = valider_joueur(data)
    if erreurs:
        return jsonify({"error": " ".join(erreurs.values()), "champs": erreurs}), 400
    try:
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    if email_existe(cur, valeurs["email"]):
                        return jsonify({"error": "Cet email est déjà utilisé par un autre joueur."}), 409
                    cur.execute(
                        "INSERT INTO joueur (nom, prenom, gsm, email) "
                        "VALUES (%s, %s, %s, %s) RETURNING id",
                        (valeurs["nom"], valeurs["prenom"], valeurs["gsm"], valeurs["email"]),
                    )
                    nouvel_id = cur.fetchone()[0]
        finally:
            conn.close()
        return jsonify({"message": "Joueur ajouté avec succès.", "id": nouvel_id}), 201
    except psycopg2.Error as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


@app.route("/api/joueurs/<int:joueur_id>", methods=["PUT"])
def modifier_joueur(joueur_id):
    data = request.get_json(silent=True) or {}
    erreurs, valeurs = valider_joueur(data)
    if erreurs:
        return jsonify({"error": " ".join(erreurs.values()), "champs": erreurs}), 400
    try:
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    if email_existe(cur, valeurs["email"], exclure_id=joueur_id):
                        return jsonify({"error": "Cet email est déjà utilisé par un autre joueur."}), 409
                    cur.execute(
                        "UPDATE joueur SET nom = %s, prenom = %s, gsm = %s, email = %s "
                        "WHERE id = %s",
                        (valeurs["nom"], valeurs["prenom"], valeurs["gsm"], valeurs["email"], joueur_id),
                    )
                    if cur.rowcount == 0:
                        return jsonify({"error": "Joueur introuvable."}), 404
        finally:
            conn.close()
        return jsonify({"message": "Joueur mis à jour avec succès."})
    except psycopg2.Error as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


@app.route("/api/joueurs/<int:joueur_id>", methods=["DELETE"])
def supprimer_joueur(joueur_id):
    try:
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM joueur WHERE id = %s", (joueur_id,))
                    if cur.rowcount == 0:
                        return jsonify({"error": "Joueur introuvable."}), 404
        finally:
            conn.close()
        return jsonify({"message": "Joueur supprimé avec succès."})
    except psycopg2.errors.ForeignKeyViolation:
        return jsonify({
            "error": "Impossible de supprimer ce joueur : il est utilisé dans le "
                     "calendrier. Réinitialisez le calendrier d'abord."
        }), 409
    except psycopg2.Error as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


# ---------- API calendrier ----------

@app.route("/api/calendrier", methods=["GET"])
def obtenir_calendrier():
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.date_sunday, cj.poste, cj.joueur_id,
                           j.nom || ' ' || j.prenom
                    FROM calendrier c
                    LEFT JOIN calendrier_joueur cj ON cj.calendrier_id = c.id
                    LEFT JOIN joueur j ON j.id = cj.joueur_id
                    ORDER BY c.date_sunday, cj.poste
                """)
                rows = cur.fetchall()
        finally:
            conn.close()
        matchs = {}
        for match_id, date_sunday, poste, joueur_id, nom_complet in rows:
            entree = matchs.setdefault(match_id, {"id": match_id, "date": str(date_sunday)})
            if poste is not None:
                entree[f"joueur{poste}_id"] = joueur_id
                entree[f"joueur{poste}"] = nom_complet
        return jsonify(list(matchs.values()))
    except (psycopg2.Error, RuntimeError) as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


@app.route("/api/calendrier/<int:match_id>", methods=["PUT"])
def modifier_match(match_id):
    data = request.get_json(silent=True) or {}
    ids = [data.get(f"joueur{i}_id") for i in range(1, 5)]
    if any(type(i) is not int for i in ids):
        return jsonify({"error": "Les 4 joueurs sont requis (identifiants entiers)."}), 400
    if len(set(ids)) != 4:
        return jsonify({"error": "Les 4 joueurs d'un match doivent être différents."}), 400
    try:
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM joueur WHERE id = ANY(%s)", (ids,))
                    if cur.fetchone()[0] != 4:
                        return jsonify({"error": "Un ou plusieurs joueurs sont introuvables."}), 404
                    cur.execute(
                        "UPDATE calendrier_joueur SET joueur_id = %s "
                        "WHERE calendrier_id = %s AND poste = %s",
                        (ids[0], match_id, 1),
                    )
                    if cur.rowcount == 0:
                        return jsonify({"error": "Match introuvable."}), 404
                    for poste, joueur_id in enumerate(ids[1:], start=2):
                        cur.execute(
                            "UPDATE calendrier_joueur SET joueur_id = %s "
                            "WHERE calendrier_id = %s AND poste = %s",
                            (joueur_id, match_id, poste),
                        )
        finally:
            conn.close()
        return jsonify({"message": "Match mis à jour avec succès."})
    except psycopg2.Error as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


@app.route("/api/calendrier/generer", methods=["POST"])
def generer():
    data = request.get_json(silent=True) or {}
    try:
        resume = generer_calendrier(force=bool(data.get("force")))
    except CalendrierError as e:
        message = str(e)
        code = 409 if "déjà généré" in message else 400
        return jsonify({"error": message}), code
    except (psycopg2.Error, RuntimeError) as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500
    return jsonify({
        "message": f"Calendrier généré : {resume['matchs_crees']} matchs "
                   f"du {resume['premier_match']} au {resume['dernier_match']}.",
        **resume,
    })


@app.route("/api/calendrier/reinitialiser", methods=["POST"])
def reinitialiser():
    try:
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM calendrier")
                    supprimes = cur.rowcount
        finally:
            conn.close()
        return jsonify({"message": f"Calendrier réinitialisé ({supprimes} matchs supprimés).",
                        "supprimes": supprimes})
    except (psycopg2.Error, RuntimeError) as e:
        return jsonify({"error": f"Erreur base de données : {e}"}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 3020)))
