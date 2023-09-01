import sqlite3

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import utils.constants as constants
from team import get_team_by_id

DB_NAME = constants.DB_NAME


class User:
    def __init__(self, username, password, team=None, team_invitation=None):
        self.username = username
        self.password = password
        self.team = team
        self.team_invitation = team_invitation


def get_user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])

    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]

        if user and check_password_hash(user.password, old_password):
            update_user_password(user.username, new_password)
            flash("Password changed successfully", "success")
        else:
            flash("Invalid old password", "danger")

    if user.team_invitation:
        invitation = get_team_by_id(user.team_invitation)
        return render_template("/user/profile.html", user=user, team_invitation=invitation)
    else:
        return render_template("/user/profile.html", user=user)


def create_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_hash = generate_password_hash(password)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            insert_query = """
                INSERT INTO users (username, password)
                VALUES (?, ?);
            """
            cursor.execute(insert_query, (username, password_hash))
            conn.commit()

        flash("Account created successfully", "success")
        return redirect(url_for("login"))
    return render_template("/user/create.html")


def get_user_by_username(username):
    user = None

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * 
            FROM users 
            WHERE username = ?
        """,
            (username,),
        )

        user_data = cursor.fetchone()

        if user_data:
            user = User(**user_data)
            if user.team is not None:
                user.team = get_team_by_id(user_data["team"])

    return user


def update_user_password(username, new_password):
    new_password_hash = generate_password_hash(new_password)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password = ?
            WHERE username = ?
        """,
            (new_password_hash, username),
        )

        conn.commit()
