import os
import sqlite3
import subprocess
from threading import Timer
from typing import Any

from flask import (flash, jsonify, redirect, render_template, request, session,
                   url_for)

import user as user_utils
import utils.constants as constants

DB_NAME = constants.DB_NAME


def fetch_ctfs_from_database(
        database_name: str = DB_NAME,
) -> list[dict[str, Any]]:
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ctfs ORDER BY id DESC")
        ctf_rows = cursor.fetchall()

        ctfs = []
        for row in ctf_rows:
            ctf = {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "solution": row[3],
                "password": row[4],
                "next_password": row[5],
                "next_text": row[6],
                "code": row[7],
                "difficulty": row[8],
                "added_by": row[9],
                "score": row[10],
            }
            ctfs.append(ctf)

    return ctfs


def ctf_app():
    if "username" not in session:
        return redirect(url_for("login"))

    ctfs: list[dict[str, Any]] = fetch_ctfs_from_database()
    top_scores = get_all_top_scores()

    return render_template("ctf/list.html", ctfs=ctfs, top_scores=top_scores)


def add_ctf():
    if "username" not in session:
        return redirect(url_for("login"))

    result = {}
    ex = {}

    if request.method == "POST":
        action = request.form.get("action")
        title = request.form["title"]
        description = request.form["description"]

        password = request.form.get("password", None)
        next_password = request.form.get("next_password", None)
        next_text = request.form.get("next_text", None)
        solution = request.form["solution"]

        difficulty = request.form["difficulty"]
        added_by = session.get("username", None)

        if difficulty == "easy":
            score = 10
        elif difficulty == "medium":
            score = 20
        elif difficulty == "hard":
            score = 30

        ex = {
            "title": title,
            "description": description,
            "difficulty": difficulty,
            "password": password,
            "solution": solution,
            "next_password": next_password,
            "next_text": next_text,
            "added_by": added_by,
            "score": score,
        }

        if action == "save":
            code = "# Write your code here"
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            insert_data = (
                title,
                description,
                solution,
                password,
                next_password,
                next_text,
                code,
                difficulty,
                added_by,
                score,
            )

            insert_query = """
                INSERT INTO ctfs (
                    title, description, solution, password, 
                    next_password, next_text,
                    code, difficulty, added_by, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(insert_query, insert_data)
            ctf_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return redirect(url_for("ctf", ctf_id=ctf_id))

        elif action == "run":
            code = request.form["code"]
            ex["code"] = code
            result, _ = run_ctf(ex, 0, code)

    return render_template("/ctf/create.html", result=result, ctf=ex)


def check_login():
    if "username" not in session:
        return False
    return True


def save_team_code(team, ctf_id, user_code):
    team_directory = os.path.join("teams", team)
    os.makedirs(team_directory, exist_ok=True)

    file_name = f"{ctf_id}.py3"
    file_path = os.path.join(team_directory, file_name)

    with open(file_path, "w") as file:
        file.write(user_code)


def get_team_code(team, ctf_id):
    file_path = os.path.join("teams", team, f"{ctf_id}.py3")
    print(file_path)
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()

    return None


def execute_and_validate(ex, user_code):
    result = {"type": "", "message": "", "stdout": "", "stderr": ""}
    expected_output = ex['solution']
    if user_code != expected_output:
        result["type"] = "danger"
        result["message"] = "That is not the correct solution."
        ex["code"] = user_code
        return result
    else:
        result["next_password"] = ex['next_password']
        result["next_text"] = ex['next_text']

    return result


def delete_ctf(ctf_id):
    if request.method == "POST":
        user_id = session["username"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM ctfs WHERE id = ? AND added_by = ?",
                (ctf_id, user_id),
            )

            cursor.execute("DELETE FROM ctf_scores WHERE ctf_id = ?", (ctf_id,))

            conn.commit()

        flash("Successfully deleted.", "success")

    return redirect(url_for("ctf_app"))


def run_ctf(ex, ctf_id, user_code):
    user = user_utils.get_user_by_username(session["username"])
    save_team_code(user.team.name, ctf_id, user_code)
    top_scores = get_top_scores(ctf_id)
    result = execute_and_validate(ex, user_code)

    if result["type"] == "danger":
        return result, top_scores

    ex["code"] = user_code

    total_score = ex["score"]
    result["type"] = "success"
    result["message"] = "That is correct!"
    result['full_score'] = True

    if ctf_id != 0:
        total_score, result = update_team_score(
            user.team.name, ctf_id, total_score, result
        )

    result["message"] += f' Your team have earned {total_score} points!'
    top_scores = get_top_scores(ctf_id)

    return result, top_scores


def update_team_score(team, ctf_id, total_score, result):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT total_score
            FROM ctf_scores
            WHERE team=? AND ctf_id=?
            """,
            (team, ctf_id),
        )
        score = cursor.fetchone()

        if score:
            if total_score > score[0]:
                result["message"] += " New record!"
                cursor.execute(
                    """
                    UPDATE ctf_scores
                    SET total_score=?
                    WHERE team=? AND ctf_id=?
                    """,
                    (total_score, team, ctf_id),
                )
        else:
            cursor.execute(
                """
                INSERT INTO ctf_scores (team, ctf_id, total_score)
                VALUES (?, ?, ?)
                """,
                (team, ctf_id, total_score),
            )

        connection.commit()

    return total_score, result


def get_top_scores(ctf_id):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        query = """
                SELECT
                    teams.name AS team,
                    teams.logo AS team_logo,
                    ctf_scores.total_score AS total_score,
                    ctf_scores.date_created
                FROM
                    teams
                LEFT JOIN
                    ctf_scores ON teams.name = ctf_scores.team
                WHERE
                    ctf_scores.ctf_id = ?
                ORDER BY
                    total_score DESC;
                """
        cursor.execute(query, (ctf_id,))
        top_scores = cursor.fetchall()

    return top_scores


def get_all_top_scores():
    try:
        with sqlite3.connect(DB_NAME) as connection:
            cursor = connection.cursor()
            query = """
                SELECT t.name AS team, t.logo, SUM(s.total_score) AS total_score, MAX(s.date_created) AS date_created
                FROM teams t
                LEFT JOIN ctf_scores s ON t.name = s.team
                GROUP BY t.name, t.logo
                ORDER BY total_score DESC;
                """

            cursor.execute(query)
            top_scores = cursor.fetchall()

            return top_scores

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []


def get_ctf_password(ctf_id):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        query = """
                SELECT
                    password
                FROM
                    ctfs
                WHERE
                    id = ?;"""
        cursor.execute(query, (ctf_id,))
        password = cursor.fetchone()

    return password


def protected_ctf(ctf_id):
    ctf_password = get_ctf_password(ctf_id)
    if ctf_password is None:
        return redirect(url_for("ctf", ctf_id=ctf_id))

    if request.method == "POST":
        user_input_password = request.form.get("password")
        if user_input_password == ctf_password[0]:
            session['ctf_' + str(ctf_id) + '_authenticated'] = True
            return redirect(url_for("ctf", ctf_id=ctf_id))
        else:
            flash("Wrong password!", "danger")
            return redirect(url_for("protected_ctf", ctf_id=ctf_id))
    return redirect(url_for("ctf", ctf_id=ctf_id))


def ctf(ctf_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])

    if user.team is None:
        flash("You need to be part of a team to access this page.", "danger")
        return render_template("/ctf/password.html", ctf_id=ctf_id)

    if (session.get('ctf_' + str(ctf_id) + '_authenticated') is None
            or session.get('ctf_' + str(ctf_id) + '_authenticated') is False):
        return render_template("/ctf/password.html", ctf_id=ctf_id)

    ctfs = fetch_ctfs_from_database()

    ex = find_ctf_by_id(ctfs, ctf_id)
    if ex is None:
        return render_template("/ctf/404.html", user=user)

    num_of_ctfs = len(ctfs)

    if request.method == "POST":
        user_code = request.form["code"]
        result, top_scores = run_ctf(ex, ctf_id, user_code)
        return render_template(
            "/ctf/ctf.html",
            ctf=ex,
            user=user,
            num_of_ctfs=num_of_ctfs,
            result=result,
            top_scores=top_scores,
        )

    print(f"{user.username} is opening... {ctf_id}")
    team_code = get_team_code(user.team.name, ctf_id)

    if team_code:
        ex["code"] = team_code
        print(team_code)

    top_scores = get_top_scores(ctf_id)
    print(top_scores)

    return render_template(
        "/ctf/ctf.html",
        ctf=ex,
        user=user,
        num_of_ctfs=num_of_ctfs,
        result={},
        top_scores=top_scores,
    )


def find_ctf_by_id(ctfs, ctf_id):
    return next((e for e in ctfs if e["id"] == ctf_id), None)
