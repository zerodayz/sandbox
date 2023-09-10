from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import datetime

from models import User
from models import db


def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.hashed_password, password):
            session["username"] = username

            user.last_login = datetime.utcnow()
            user.last_login_ip = request.remote_addr

            db.session.commit()

            return redirect(url_for("exercise_app"))
        else:
            flash("Invalid credentials", "error")

    if "username" in session:
        return redirect(url_for("exercise_app"))

    return render_template("user/login.html")


def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
