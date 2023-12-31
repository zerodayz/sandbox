from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import pytz

import utils.constants as constants

from models import db
from models import User, Team, TeamInvitation, ExerciseScore

DB_NAME = constants.DB_NAME


def user_profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_team = []

    user = User.query.filter_by(username=username).first()
    if request.method == "POST":
        old_password = request.form.get("old_password", None)
        new_password = request.form.get("new_password", None)

        if old_password and new_password:
            if user and check_password_hash(user.hashed_password, old_password):
                user.hashed_password = generate_password_hash(new_password)
                db.session.commit()
                flash("Password changed successfully", "success")
            else:
                flash("Invalid old password", "danger")

        if request.form.get("timezone", None):
            user.timezone = request.form.get("timezone", None)
            db.session.commit()
            flash("Timezone changed successfully", "success")

    if user.team_id:
        team_id = user.team_id
        user_team = Team.query.get(team_id)

    team_invitations = TeamInvitation.query.filter_by(user_id=user.id).all()
    timezones = pytz.all_timezones

    if team_invitations:
        teams = []
        for invitation in team_invitations:
            team = Team.query.get(invitation.team_id)
            teams.append(team)
        return render_template("user/profile.html", timezones=timezones, user=user, team=user_team, team_invitations=teams)
    else:
        return render_template("user/profile.html", timezones=timezones, user=user, team=user_team)


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


def get_all_top_scores():
    try:
        top_scores = (
            db.session.query(
                User.username,
                db.func.sum(ExerciseScore.total_score).label('total_score'),
                db.func.max(ExerciseScore.date_created).label('last_date_created'),
                Team.logo,
                db.func.sum(ExerciseScore.execution_time).label('execution_time')
            )
            .outerjoin(ExerciseScore, User.id == ExerciseScore.user_id)
            .outerjoin(Team, User.team_id == Team.id)
            .group_by(User.username, Team.logo)
            .order_by(db.desc('total_score'), 'execution_time')
            .having(db.func.sum(ExerciseScore.total_score) > 0)
            .all()
        )

        return top_scores

    except Exception as e:
        print(f"Database error: {e}")
        return []


def user_dashboard():
    try:
        top_scores = get_all_top_scores()
        return render_template("/user/dashboard.html", top_scores=top_scores)

    except Exception as e:
        flash(f"Error: {e}", "danger")
        return render_template("/user/dashboard.html", top_scores=[])