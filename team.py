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
        return render_template("/team/get.html", user=user)

    try:
        team_crest = request.files["team_crest"]
        img = Image.open(team_crest)
        img = img.resize((24, 24))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        team_crest_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        team_name = request.form["team_name"]
        team_password = request.form["team_password"]

        user = user_utils.get_user_by_username(session["username"])
        owner = user.username

        new_password_hash = generate_password_hash(team_password)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            insert_team_query = """
                INSERT INTO teams (name, owner, password, logo)
                VALUES (?, ?, ?, ?);
            """
            cursor.execute(
                insert_team_query, (team_name, owner, new_password_hash, team_crest_b64)
            )

            update_user_query = """
                UPDATE users
                SET team = ?
                WHERE username = ?;
            """
            cursor.execute(update_user_query, (cursor.lastrowid, owner))

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
