import base64
import io

from sqlite3 import IntegrityError

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from PIL import Image
from werkzeug.security import check_password_hash, generate_password_hash

import apps.user as user_utils

from apps.apps import decode_team_logo

from models import db
from models import User, Team, Ctf, CtfScore, Exercise, ExerciseScore, TeamInvitation

from sqlalchemy import func, desc


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
    try:
        team_scores = (
            db.session.query(
                Team.name.label('TeamName'),
                func.sum(ExerciseScore.total_score).label('TotalScore'),
                func.max(ExerciseScore.date_created).label('LastScoreUpdateDate'),
                Team.logo.label('TeamLogo'),
            )
            .join(User.team)
            .join(ExerciseScore, ExerciseScore.user_id == User.id)
            .group_by(Team.name, Team.logo)
            .having(func.sum(ExerciseScore.total_score) > 0)
            .order_by(desc('TotalScore'))
            .all()
        )
        team_scores = decode_team_logo(team_scores)

        ctf_team_scores = (
            db.session.query(
                Team.name.label('TeamName'),
                db.func.sum(CtfScore.total_score).label('TeamScore'),
                db.func.max(CtfScore.date_created).label('LastScoreUpdateDate'),
                Team.logo.label('TeamLogo'),
            )
            .join(CtfScore, Team.id == CtfScore.team_id)
            .join(Ctf, CtfScore.ctf_id == Ctf.id)
            .group_by(Team.name, Team.logo)
            .order_by(db.func.sum(CtfScore.total_score).desc())
            .all()
        )
        ctf_team_scores = decode_team_logo(ctf_team_scores)

        return render_template("/team/dashboard.html", top_scores=team_scores, ctf_top_scores=ctf_team_scores)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return render_template("/team/dashboard.html", top_scores=[], ctf_top_scores=[])


def update_user_invitation(username, team_id):
    try:
        user = User.query.filter_by(username=username).first()
        team = Team.query.get(team_id)
        if user and team:
            new_invitation = TeamInvitation(team_id=team_id, user_id=user.id)
            db.session.add(new_invitation)
            db.session.commit()
        else:
            flash("User or Team not found.", "danger")
    except Exception as e:
        flash(f"Error: {e}", "danger")


def delete_team():
    if request.method == "POST":
        username = session["username"]

        try:
            user = User.query.filter_by(username=username).first()
            team = Team.query.filter_by(owner_id=user.id).first()
            if team:
                CtfScore.query.filter_by(team_id=team.id).delete()
                TeamInvitation.query.filter_by(team_id=team.id).delete()

                db.session.delete(team)
                db.session.commit()
                flash("Successfully deleted team.", "success")
            else:
                flash("Team not found.", "danger")
        except Exception as e:
            flash(f"Error: {e}", "danger")

    return redirect(url_for("user_profile"))


def leave_team():
    if request.method == "POST":
        username = session["username"]
        members = User.query.filter_by(username=username).first().team
        if len(members) == 1:
            flash("You are the last member of the team. Please delete the team instead.", "danger")
            return redirect(url_for("get_user_team"))
        try:
            user = User.query.filter_by(username=username).first()

            if user:
                user.team = None
                db.session.commit()
                flash("Successfully left team.", "success")
            else:
                flash("User not found.", "danger")
        except Exception as e:
            flash(f"Error: {e}", "danger")

    return redirect(url_for("user_profile"))


def join_team():
    if request.method == "POST":
        team_id = request.form["team_id"]
        username = request.form["username"]
        team_password = request.form["team_password"]
        mode = request.form["mode"]

        if mode == "reject":
            try:
                user = User.query.filter_by(username=username).first()
                team = Team.query.get(team_id)
                if user and team:
                    TeamInvitation.query.filter_by(team_id=team_id, user_id=user.id).delete()
                    db.session.commit()
                else:
                    flash("User or Team not found.", "danger")
            except Exception as e:
                flash(f"Error: {e}", "danger")
            return redirect(url_for("user_profile"))

        if mode == "accept":
            members = User.query.filter_by(username=username).first().team
            if members:
                flash("You are already member of a team. Please leave the team first.", "danger")
                return redirect(url_for("get_user_team"))

            team = Team.query.get(team_id)
            if team:
                if check_password_hash(team.hashed_password, team_password):
                    try:
                        user = User.query.filter_by(username=username).first()
                        user.team = [team]
                        user.team_invitation = None

                        db.session.commit()

                        flash(
                            f"Successfully joined team '{team.name}'. Congratulations!",
                            "success",
                        )
                    except IntegrityError:
                        db.session.rollback()
                        flash("User already belongs to a team.", "danger")
                else:
                    flash("Invalid team password.", "danger")
            else:
                flash(f"Team with ID {team_id} does not exist.", "danger")

            return redirect(url_for("get_user_team"))


def update_user_team():
    username = session["username"]

    try:
        user = User.query.filter_by(username=username).first()
        if not user.team and user.team.owner_id != user.id:
            flash("You are not the owner of this team.", "danger")
            return redirect(url_for("user_profile"))

        new_team_name = request.form.get("team_name", None)

        existing_team = Team.query.filter_by(name=new_team_name).first()
        if existing_team:
            flash("Team name already taken. Please choose another one.", "danger")
            return redirect(url_for("get_user_team"))

        team = user.team[0]

        team_crest = request.files.get("team_crest", None)
        if team_crest:
            img = Image.open(team_crest)
            target_size = (24, 24)
            img.thumbnail(target_size, Image.LANCZOS)

            output_img = Image.new("RGBA", target_size, (0, 0, 0, 0))

            left = (target_size[0] - img.width) // 2
            top = (target_size[1] - img.height) // 2

            output_img.paste(img, (left, top))

            buffered = io.BytesIO()
            output_img.save(buffered, format="PNG")
            team_crest_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            team_crest_b64 = team_crest_b64.encode("utf-8")
            team.logo = team_crest_b64

        if new_team_name:
            team.name = new_team_name

        db.session.commit()

        flash("Team successfully updated.", "success")

    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("user_profile"))


def get_user_team():
    username = session["username"]
    if request.method == "GET":
        user = User.query.filter_by(username=username).first()
        user_team = []
        if len(user.team):
            team_id = user.team[0].id
            user_team = Team.query.get(team_id)

        return render_template("/team/team.html", user=user, team=user_team)

    try:
        user = User.query.filter_by(username=username).first()

        if user.team:
            flash("You are already part of a team.", "danger")
            return redirect(url_for("user_profile"))

        team_name = request.form["team_name"]

        existing_team = Team.query.filter_by(name=team_name).first()
        if existing_team:
            flash("Team name already taken. Please choose another one.", "danger")
            return redirect(url_for("get_user_team"))

        team_crest = request.files.get("team_crest", None)
        if not team_crest:
            team_crest_b64 = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAACXBIWXMAAAsTAAALEwEAmpwYAAACRElEQVRIiZ2V3W6jMBCFPxtooDRJo6KqN1Uu+v4P0seoepFGipREBUod7NmLlS2S5U9rKSLA+JyZ8TmDen9/F2YsEUHkb6hSCqXUnG3EU6DOOaIoIk1T7u7uADDG0DQNIoLW+v8InHPEcczz8zNFUZCmKVEUAWCtpa5rdrsdp9NplKSXwDnHZrNhu92yWCxCe/xPa81qtWK5XLLf7/n4+BgkGaRu25YkSRARlFKICG3bht5baxERXl5eWK/XOOfmV6C15nw+8/n5yevrK19fXxwOB9q2Jc9zttttIAd4fHzkdDr1Ewwxa63Z7/ecz2fKsgzKqaqKKIp4e3vDWgtAkiQ453qVFT89PV098C3x/0WE+/v7cO+cI8/zkL2IEMcxRVH0nkO82WxCj/26ve+SLxYL8jwPPfdxt4lOtqgPPMuyq+y11vz8/GCMGdw3arQxcKUUdV1T1/Xo3nioHV3wJEkCuFIK5xxlWfL7+zs5MmZVkGXZFWFZlhhjZs0jPZY9/G2FV4dSCmstl8tl9sAbn1SdrD2gc+5Kon0k3WfhDIayERGMMSHGj4uuV7rneIsTezeOraqqgu67LetL5p8KpmTmV5ZlpGlK0zRUVTXZf/9+UEW+bOccq9WKoigAWK/XHA4Hvr+/A0if1IMZh5i7bl0ul4FMRHh4eJj9ydS3gUMz6DbbbtyQ1JVS0z4QEY7HI23borXmcrlwPB57wbpXv3fSyUopmqZht9uRJAnGGKy1QapdT/RV00vQ9UZX/0Me6AP26w+R334wsxKa7gAAAABJRU5ErkJggg=="
        else:
            img = Image.open(team_crest)
            target_size = (24, 24)
            img.thumbnail(target_size, Image.LANCZOS)

            output_img = Image.new("RGBA", target_size, (0, 0, 0, 0))

            left = (target_size[0] - img.width) // 2
            top = (target_size[1] - img.height) // 2

            output_img.paste(img, (left, top))

            buffered = io.BytesIO()
            output_img.save(buffered, format="PNG")
            team_crest_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        team_password = request.form["team_password"]

        new_password_hash = generate_password_hash(team_password)

        team_crest_b64 = team_crest_b64.encode("utf-8")
        new_team = Team(name=team_name, owner_id=user.id, hashed_password=new_password_hash, logo=team_crest_b64)
        db.session.add(new_team)
        db.session.commit()

        team_id = Team.query.filter_by(name=team_name).first().id
        user.team_id = team_id
        db.session.commit()

        flash("Team successfully created.", "success")

    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("user_profile"))
