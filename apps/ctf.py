import os

from flask import (flash, jsonify, redirect, render_template, request, session,
                   url_for)

import apps.user as user_utils
import utils.constants as constants

from models import db
from models import User, Ctf, CtfScore, Team
from models import DifficultyEnum

from sqlalchemy import or_

from apps.apps import decode_team_logo

DB_NAME = constants.DB_NAME


def fetch_ctfs_from_database():
    ctfs = Ctf.query.order_by(Ctf.id.desc()).all()

    ctfs_list = []
    for ctf in ctfs:
        ctf_dict = {
            "id": ctf.id,
            "title": ctf.title,
            "description": ctf.description.decode("utf-8"),
            "solution": ctf.solution,
            "password": ctf.ctf_password,
            "next_password": ctf.next_password,
            "next_text": ctf.next_text,
            "code": ctf.code,
            "ctf_difficulty": ctf.ctf_difficulty,
            "added_by_user_id": ctf.added_by_user_id,
            "score": ctf.score,
        }
        ctfs_list.append(ctf_dict)

    return ctfs_list


def ctf_app():
    if "username" not in session:
        return redirect(url_for("login"))

    page = request.args.get('page', 1, type=int)
    items_per_page = 10

    search_query = request.args.get('query', '')

    ctfs = Ctf.query.filter(
        or_(
            Ctf.title.ilike(f"%{search_query}%"),
        )
    ).order_by(Ctf.id.desc()).paginate(
        page=page,
        per_page=items_per_page,
        error_out=False
    )

    # ctfs = fetch_ctfs_from_database()

    top_scores = get_all_top_scores()
    top_scores = decode_team_logo(top_scores)

    return render_template("ctf/list.html", query=search_query, ctfs=ctfs, top_scores=top_scores)


def add_ctf():
    if "username" not in session:
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    if len(user.team) == 0:
        flash("You need to be part of a team to access this page.", "danger")
        return redirect(url_for("ctf_app"))

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

        ctf_difficulty = request.form["difficulty"]
        username = session.get("username", None)
        added_by_user_id = User.query.filter_by(username=username).first().id

        if ctf_difficulty == "Easy":
            insert_difficulty = DifficultyEnum.Easy
            score = 10
        elif ctf_difficulty == "Medium":
            insert_difficulty = DifficultyEnum.Medium
            score = 20
        elif ctf_difficulty == "Hard":
            insert_difficulty = DifficultyEnum.Hard
            score = 30

        ex = {
            "title": title,
            "description": description,
            "ctf_difficulty": ctf_difficulty,
            "ctf_password": password,
            "solution": solution,
            "next_password": next_password,
            "next_text": next_text,
            "added_by_user_id": added_by_user_id,
            "score": score,
        }

        if action == "save":
            ctf = Ctf(
                title=title,
                description=description.encode("utf-8"),
                ctf_password=password,
                next_password=next_password,
                next_text=next_text,
                solution=solution,
                code="# Write your code here",
                ctf_difficulty=insert_difficulty,
                added_by_user_id=added_by_user_id,
                score=score,
            )

            db.session.add(ctf)
            db.session.commit()

            return redirect(url_for("ctf", ctf_id=ctf.id))

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
        username = session["username"]
        user_id = User.query.filter_by(username=username).first().id

        ctf = Ctf.query.filter_by(id=ctf_id, added_by_user_id=user_id).first()
        if ctf:
            db.session.delete(ctf)
            CtfScore.query.filter_by(ctf_id=ctf_id).delete()

            db.session.commit()

            flash("Successfully deleted.", "success")
        else:
            flash("Permission denied.", "danger")

    return redirect(url_for("ctf_app"))


def run_ctf(ex, ctf_id, user_code):
    user = user_utils.get_user_by_username(session["username"])
    team_id = user.team[0].id
    user_team = Team.query.get(team_id)
    save_team_code(user_team.name, ctf_id, user_code)

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
            user_team.id, ctf_id, total_score, result
        )

    result["message"] += f' Your team have earned {total_score} points!'
    top_scores = get_top_scores(ctf_id)
    top_scores = decode_team_logo(top_scores)

    return result, top_scores


def update_team_score(team_id, ctf_id, total_score, result):
    ctf_score = CtfScore.query.filter_by(team_id=team_id, ctf_id=ctf_id).first()
    if ctf_score:
        if total_score > ctf_score.total_score:
            ctf_score.total_score = total_score
            db.session.commit()
    else:
        ctf_score = CtfScore(team_id=team_id, ctf_id=ctf_id, total_score=total_score)
        db.session.add(ctf_score)
        db.session.commit()

    return total_score, result


def get_top_scores(ctf_id):
    top_scores = (
        db.session.query(Team.name.label('team'),
                         CtfScore.total_score.label('total_score'),
                         CtfScore.date_created,
                         Team.logo.label('team_logo'),)
        .join(CtfScore, Team.id == CtfScore.team_id)
        .filter(CtfScore.ctf_id == ctf_id)
        .order_by(CtfScore.total_score.desc())
        .limit(5)
        .all()
    )

    return top_scores


def get_all_top_scores():
    try:
        top_scores = (
            db.session.query(Team.name.label('team'),
                             db.func.sum(CtfScore.total_score).label('total_score'),
                             db.func.max(CtfScore.date_created).label('last_date_created'),
                             Team.logo.label('team_logo'))
            .join(CtfScore, Team.id == CtfScore.team_id)
            .join(Ctf, CtfScore.ctf_id == Ctf.id)
            .group_by(Team.name, Team.logo)
            .order_by(db.func.sum(CtfScore.total_score).desc())
            .limit(5)
            .all()
        )

        return top_scores

    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_ctf_password(ctf_id):
    ctf = Ctf.query.get(ctf_id)

    if ctf:
        return ctf.ctf_password
    else:
        return None


def protected_ctf(ctf_id):
    ctf_password = get_ctf_password(ctf_id)
    if ctf_password is None:
        session['ctf_' + str(ctf_id) + '_authenticated'] = True
        return redirect(url_for("ctf", ctf_id=ctf_id))

    if request.method == "POST":
        user_input_password = request.form.get("password")
        if user_input_password == ctf_password:
            session['ctf_' + str(ctf_id) + '_authenticated'] = True
            return redirect(url_for("ctf", ctf_id=ctf_id))
        else:
            flash("Wrong password!", "danger")
            return render_template("/ctf/password.html", ctf_id=ctf_id)
    return render_template("/ctf/password.html", ctf_id=ctf_id)


def ctf(ctf_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])

    if len(user.team) == 0:
        flash("You need to be part of a team to access this page.", "danger")
        return render_template("/ctf/password.html", ctf_id=ctf_id)

    if (session.get('ctf_' + str(ctf_id) + '_authenticated') is None
            or session.get('ctf_' + str(ctf_id) + '_authenticated') is False):
        return redirect(url_for("protected_ctf", ctf_id=ctf_id))

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

    team_id = user.team[0].id
    user_team = Team.query.get(team_id)

    print(f"{user.username} is opening... {ctf_id}")
    team_code = get_team_code(user_team.name, ctf_id)

    if team_code:
        ex["code"] = team_code
        print(team_code)

    top_scores = get_top_scores(ctf_id)
    top_scores = decode_team_logo(top_scores)

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
