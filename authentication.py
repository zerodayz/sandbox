from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from user import get_user_by_username


def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = get_user_by_username(username)
        if user and check_password_hash(user.password, password):
            session["username"] = username
            return redirect(url_for("exercise_app"))
        else:
            flash("Invalid credentials", "error")

    if "username" in session:
        return redirect(url_for("exercise_app"))
    
    return render_template("/user/login.html")


def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
