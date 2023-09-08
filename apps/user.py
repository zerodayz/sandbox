from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import utils.constants as constants

from models import db
from models import User, Team

DB_NAME = constants.DB_NAME


def user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    user = User.query.filter_by(username=username).first()
    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]

        if user and check_password_hash(user.password, old_password):
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Password changed successfully", "success")
        else:
            flash("Invalid old password", "danger")

    if user.team:
        user.team.logo = user.team.logo.decode("utf-8")

    if user.team_invitation:
        team = Team.query.get(user.team_invitation)
        if team:
            return render_template("user/profile.html", user=user, team_invitation=team)
        else:
            user.team_invitation = None
            db.session.commit()
            return render_template("user/profile.html", user=user)
    else:
        return render_template("user/profile.html", user=user)


def create_user():
    if request.method == "POST":
        username = request.form["username"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken. Please choose another one.", "danger")
            return render_template("user/create.html")

        password = request.form["password"]
        password_hash = generate_password_hash(password)

        new_user = User(username=username, password=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully", "success")
        return redirect(url_for("login"))

    return render_template("user/create.html")


def get_user_by_username(username):
    user = None

    try:
        user = User.query.filter_by(username=username).first()

        if user:
            if user.team_id is not None:
                user.team = Team.query.get(user.team_id)

    except Exception as e:
        flash(f"Error: {e}", "danger")

    return user
