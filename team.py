import base64
import io
import sqlite3

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

import user as user_utils
import utils.constants as constants

DB_NAME = constants.DB_NAME


class Team:
    def __init__(self, team_id, name, owner, date_created, logo, password):
        self.id = team_id
        self.name = name
        self.owner = owner
        self.date_created = date_created
        self.logo = logo
        self.password = password


def invite_user_to_team():
    if request.method == "POST":
        username = request.form["invite_member"]
        team_id = request.form["team_id"]

        user = user_utils.get_user_by_username(username)
        if user:
            update_user_invitation(username, team_id)
            flash(f"User '{username}' successfully invited to team.", "success")
        else:
            flash(f"User '{username}' does not exist.", "error")

    return redirect(url_for("get_user_team"))


def get_teams_dashboard():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        select_query = """
            SELECT
                t.name AS TeamName,
                t.logo AS TeamLogo,
                SUM(s.total_score) AS TeamScore,
                MAX(s.date_created) AS LastScoreUpdateDate,
                COUNT(DISTINCT u.username) AS NumberOfMembers
            FROM
                teams t
            JOIN
                users u ON t.id = u.team
            LEFT JOIN
                scores s ON u.username = s.username
            GROUP BY
                t.name, t.logo
            ORDER BY TeamScore DESC
            """
        cursor.execute(select_query)
        team_score = cursor.fetchall()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        select_query = """
                    SELECT
                        teams.name AS team,
                        teams.logo AS team_logo,
                        SUM(ctf_scores.total_score) AS total_score,
                        MAX(ctf_scores.date_created) AS last_date_created
                    FROM
                        ctf_scores
                    JOIN
                        ctfs ON ctf_scores.ctf_id = ctfs.id
                    JOIN
                        teams ON ctf_scores.team = teams.name
                    GROUP BY
                        teams.name, teams.logo
                    ORDER BY total_score DESC"""

        cursor.execute(select_query)
        ctf_team_score = cursor.fetchall()

    return render_template("/team/dashboard.html", top_scores=team_score, ctf_top_scores=ctf_team_score)


def update_user_invitation(username, team_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        update_query = """
            UPDATE users
            SET team_invitation = ?
            WHERE username = ?;
        """
        cursor.execute(update_query, (team_id, username))
        conn.commit()


def delete_team():
    if request.method == "POST":
        user_id = session["username"]

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            select_query = """
                SELECT id
                FROM teams
                WHERE owner = ?;
                """
            cursor.execute(select_query, (user_id,))
            team_id = cursor.fetchone()[0]

            delete_ctf_scores_query = """
                DELETE FROM ctf_scores
                WHERE team = ?;
                """
            cursor.execute(delete_ctf_scores_query, (team_id,))

            update_query = """
                UPDATE users
                SET team = NULL
                WHERE team = ?;
                """
            cursor.execute(update_query, (team_id,))

            delete_query = """
                DELETE FROM teams
                WHERE id = ?;
                """
            cursor.execute(delete_query, (team_id,))
            conn.commit()

        flash("Successfully deleted team.", "success")

    return redirect(url_for("get_user_profile"))


def leave_team():
    if request.method == "POST":
        user_id = session["username"]

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            update_sql = """
                UPDATE users
                SET team = NULL
                WHERE username = ?;
            """
            cursor.execute(update_sql, (user_id,))
            conn.commit()

        flash("Successfully left team.", "success")

    return redirect(url_for("get_user_profile"))


def join_team():
    if request.method == "POST":
        team_id = request.form["team_id"]
        user_id = request.form["user_id"]
        team_password = request.form["team_password"]

        team = get_team_by_id(team_id)

        if team:
            if check_password_hash(team.password, team_password):
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()

                    update_query = """
                        UPDATE users
                        SET team = ?, team_invitation = null
                        WHERE username = ?;
                        """
                    cursor.execute(update_query, (team_id, user_id))
                    conn.commit()

                    flash(
                        f"Successfully joined team '{team.name}'. Congratulations!",
                        "success",
                    )
            else:
                flash("Invalid team password.", "danger")
        else:
            flash(f"Team with ID {team_id} does not exist.", "danger")

        return redirect(url_for("get_user_team"))


def get_user_team():
    if request.method == "GET":
        user = user_utils.get_user_by_username(session["username"])
        return render_template("/team/team.html", user=user)

    try:
        user = user_utils.get_user_by_username(session["username"])
        if user.team:
            flash("You are already part of a team.", "danger")
            return redirect(url_for("get_user_profile"))

        team_name = request.form["team_name"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            select_query = """
                SELECT id
                FROM teams
                WHERE name = ?;
                """
            cursor.execute(select_query, (team_name,))
            team_id = cursor.fetchone()

            if team_id:
                flash("Team name already taken. Please choose another one.", "danger")
                return redirect(url_for("get_user_team"))

        team_crest = request.files.get("team_crest", None)
        if not team_crest:
            team_crest_b64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAACRElEQVRIiZ2V3W6jMBCFPxtooDRJo6KqN1Uu+v4P0seoepFGipREBUod7NmLlS2S5U9rKSLA+JyZ8TmDen9/F2YsEUHkb6hSCqXUnG3EU6DOOaIoIk1T7u7uADDG0DQNIoLW+v8InHPEcczz8zNFUZCmKVEUAWCtpa5rdrsdp9NplKSXwDnHZrNhu92yWCxCe/xPa81qtWK5XLLf7/n4+BgkGaRu25YkSRARlFKICG3bht5baxERXl5eWK/XOOfmV6C15nw+8/n5yevrK19fXxwOB9q2Jc9zttttIAd4fHzkdDr1Ewwxa63Z7/ecz2fKsgzKqaqKKIp4e3vDWgtAkiQ453qVFT89PV098C3x/0WE+/v7cO+cI8/zkL2IEMcxRVH0nkO82WxCj/26ve+SLxYL8jwPPfdxt4lOtqgPPMuyq+y11vz8/GCMGdw3arQxcKUUdV1T1/Xo3nioHV3wJEkCuFIK5xxlWfL7+zs5MmZVkGXZFWFZlhhjZs0jPZY9/G2FV4dSCmstl8tl9sAbn1SdrD2gc+5Kon0k3WfhDIayERGMMSHGj4uuV7rneIsTezeOraqqgu67LetL5p8KpmTmV5ZlpGlK0zRUVTXZf/9+UEW+bOccq9WKoigAWK/XHA4Hvr+/A0if1IMZh5i7bl0ul4FMRHh4eJj9ydS3gUMz6DbbbtyQ1JVS0z4QEY7HI23borXmcrlwPB57wbpXv3fSyUopmqZht9uRJAnGGKy1QapdT/RV00vQ9UZX/0Me6AP26w+R334wsxKa7gAAAABJRU5ErkJggg=="
        else:
            img = Image.open(team_crest)
            img = img.resize((24, 24))
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            team_crest_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        team_password = request.form["team_password"]

        user = user_utils.get_user_by_username(user.username)

        new_password_hash = generate_password_hash(team_password)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            insert_team_query = """
                INSERT INTO teams (name, owner, password, logo)
                VALUES (?, ?, ?, ?);
            """
            cursor.execute(
                insert_team_query, (team_name, user.username, new_password_hash, team_crest_b64)
            )

            update_user_query = """
                UPDATE users
                SET team = ?
                WHERE username = ?;
            """
            cursor.execute(update_user_query, (cursor.lastrowid, user.username))

            conn.commit()

        flash("Team successfully created.", "success")

    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("get_user_profile"))


def get_team_by_id(team_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            select_query = """
                SELECT id, name, owner, date_created, logo, password
                FROM teams
                WHERE id = ?;
            """
            cursor.execute(select_query, (team_id,))
            team_data = cursor.fetchone()

            if team_data:
                team_id, name, owner, date_created, logo, password = team_data
                return Team(team_id, name, owner, date_created, logo, password)

    except sqlite3.Error as e:
        flash(f"Error: {e}", "danger")
        pass

    return None
