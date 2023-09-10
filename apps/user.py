from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import utils.constants as constants

from models import db
from models import User, Team, TeamInvitation

DB_NAME = constants.DB_NAME


def user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_team = []

    user = User.query.filter_by(username=username).first()
    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]

        if user and check_password_hash(user.hashed_password, old_password):
            user.hashed_password = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully", "success")
        else:
            flash("Invalid old password", "danger")

    if len(user.team):
        team_id = user.team[0].id
        user_team = Team.query.get(team_id)

    team_invitations = TeamInvitation.query.filter_by(user_id=user.id).all()
    if team_invitations:
        teams = []
        for invitation in team_invitations:
            team = Team.query.get(invitation.team_id)
            teams.append(team)
        return render_template("user/profile.html", user=user, team=user_team, team_invitations=teams)
    else:
        return render_template("user/profile.html", user=user, team=user_team)


def create_user():
    if request.method == "POST":
        username = request.form["username"]

        existing_user = User.query.filter(
            db.func.lower(User.username) == db.func.lower(username)
        ).first()
        if existing_user:
            flash("Username already taken. Please choose another one.", "danger")
            return render_template("user/create.html")

        password = request.form["password"]
        password_hash = generate_password_hash(password)

        new_user = User(username=username, hashed_password=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully", "success")
        return redirect(url_for("login"))

    return render_template("user/create.html")


def get_user_by_username(username):
    user = None

    try:
        user = User.query.filter_by(username=username).first()

    except Exception as e:
        flash(f"Error: {e}", "danger")

    return user
