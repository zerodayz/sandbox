from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)

from models import db
from models import User
import pytz

from apps.apps import add_exercise, delete_exercise, exercise, exercise_app, download_exercises
from apps.authentication import login, logout
from apps.team import (delete_team, get_user_team, invite_user_to_team, join_team,
                       leave_team, get_teams_dashboard, update_user_team)
from apps.user import user_profile, create_user, user_dashboard
from apps.ctf import add_ctf, delete_ctf, ctf, ctf_app, protected_ctf
from apps.upload import upload_file, serve_uploaded_file
from apps.challenge import challenge_checksum
from apps.forum import (create_post, delete_comment, delete_post, forum_board, forum_search, edit_post,
                        create_new_as_template,
                        view_post, create_category, edit_category, delete_category, view_category)
from flask_migrate import Migrate

# import logging
# logger = logging.getLogger('sqlalchemy')
# logger.setLevel(logging.DEBUG)
# handler = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sandbox_db.sqlite'
# app.config['SQLALCHEMY_ECHO'] = True
app.config['UPLOAD_FOLDER'] = 'uploads'


def convert_to_user_timezone(date):
    username = session["username"]
    user = User.query.filter_by(username=username).first()
    if user:
        timezone = user.timezone
        if timezone:
            utc = pytz.timezone('UTC')
            utc_date = utc.localize(date)
            user_timezone = pytz.timezone(timezone)
            date = utc_date.astimezone(user_timezone)
            date = date.replace(tzinfo=None)
    return date


app.jinja_env.filters['to_user_timezone'] = convert_to_user_timezone

db.init_app(app)
migrate = Migrate(app, db)

# Configure session settings
app.secret_key = "your-secret-key"

# Register the authentication routes
app.route("/", methods=["GET", "POST"])(login)
app.route("/logout", methods=["GET"])(logout)

# Register the upload route
app.route("/upload", methods=["POST"])(upload_file)
app.route('/uploads/<filename>')(serve_uploaded_file)

# Register the page routes
app.route("/about", methods=["GET"])(lambda: render_template("about.html"))

# Register the user routes
app.route("/user/profile", methods=["GET", "POST"])(user_profile)
app.route("/user/create", methods=["GET", "POST"])(create_user)

# Register the users routes
app.route("/users/dashboard", methods=["GET"])(user_dashboard)

# Register the team routes
app.route("/team", methods=["GET", "POST"])(get_user_team)
app.route("/team/update", methods=["POST"])(update_user_team)
app.route("/team/invite", methods=["POST"])(invite_user_to_team)
app.route("/team/join", methods=["POST"])(join_team)
app.route("/team/leave", methods=["POST"])(leave_team)
app.route("/team/delete", methods=["POST"])(delete_team)

# Register the teams routes
app.route("/teams", methods=["GET"])(get_teams_dashboard)

# Register the CTF routes
app.route("/ctf", methods=["GET"])(ctf_app)
app.route("/ctf/<int:ctf_id>", methods=["GET", "POST"])(ctf)
app.route("/protected_ctf/<int:ctf_id>", methods=["GET", "POST"])(protected_ctf)
app.route("/ctf/create", methods=["GET", "POST"])(add_ctf)
app.route("/ctf/<int:ctf_id>/delete", methods=["POST"])(delete_ctf)
app.route("/ctf/challenge/checksum", methods=["POST"])(challenge_checksum)

# Register the exercises routes
app.route("/exercises", methods=["GET"])(exercise_app)
app.route("/exercises/download", methods=["GET"])(download_exercises)
app.route("/exercise/<int:exercise_id>", methods=["GET", "POST"])(exercise)
app.route("/exercise/create", methods=["GET", "POST"])(add_exercise)
app.route("/exercise/<int:exercise_id>/delete", methods=["POST"])(delete_exercise)

# Register the forum routes
app.route("/forum", methods=["GET"])(forum_board)
app.route("/forum/search", methods=["GET", "POST"])(forum_search)
app.route("/forum/post/create", methods=["GET", "POST"])(create_post)
app.route("/forum/post/<int:post_id>", methods=["POST", "GET"])(view_post)
app.route("/forum/post/<int:post_id>/edit", methods=["POST", "GET"])(edit_post)
app.route("/forum/post/<int:post_id>/delete", methods=["POST"])(delete_post)
app.route("/forum/post/<int:post_id>/create", methods=["GET", "POST"])(create_new_as_template)
app.route("/forum/comment/<int:comment_id>/delete", methods=["POST"])(delete_comment)
app.route("/forum/category/<int:category_id>", methods=["GET"])(view_category)
app.route('/forum/category/create', methods=["GET", "POST"])(create_category)
app.route('/forum/category/edit/<int:category_id>', methods=["GET", "POST"])(edit_category)
app.route('/forum/category/delete/<int:category_id>', methods=["POST"])(delete_category)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5001)
