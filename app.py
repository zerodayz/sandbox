from flask import (Flask, jsonify, redirect, render_template, request, session,
                   url_for)

from apps.apps import add_exercise, delete_exercise, exercise, exercise_app
from authentication import login, logout
from team import (delete_team, get_user_team, invite_user_to_team, join_team,
                  leave_team)
from user import get_user_profile

app = Flask(__name__)

# Configure session settings
app.secret_key = "your-secret-key"

# Register the authentication routes
app.route("/", methods=["GET", "POST"])(login)
app.route("/logout", methods=["GET"])(logout)
app.route("/profile", methods=["GET", "POST"])(get_user_profile)

# Register the team routes
app.route("/team", methods=["GET", "POST"])(get_user_team)
app.route("/team/invite", methods=["POST"])(invite_user_to_team)
app.route("/team/join", methods=["POST"])(join_team)
app.route("/team/leave", methods=["POST"])(leave_team)
app.route("/team/delete", methods=["POST"])(delete_team)

# Register the exercises routes
app.route("/exercises", methods=["GET"])(exercise_app)
app.route("/exercise/<int:exercise_id>", methods=["GET", "POST"])(exercise)
app.route("/exercise/add", methods=["GET", "POST"])(add_exercise)
app.route("/exercise/<int:exercise_id>/delete", methods=["POST"])(delete_exercise)

if __name__ == "__main__":
    app.run(debug=True, port=5001)
