import os
import tarfile
import subprocess
from threading import Timer

from flask import (flash, jsonify, redirect, render_template, request, session,
                   url_for, send_from_directory)

import apps.user as user_utils
import utils.constants as constants

from sqlalchemy import or_

from models import Exercise, ExerciseScore, Team, User
from models import DifficultyEnum
from models import db

import re

DB_NAME = constants.DB_NAME


def fetch_exercises_from_database():
    exercises = Exercise.query.order_by(Exercise.id.desc()).all()

    exercise_dicts = []
    for exercise in exercises:
        exercise_dict = {
            "id": exercise.id,
            "title": exercise.title,
            "description": exercise.description,
            "sample_1_input": exercise.sample_1_input,
            "sample_1_output": exercise.sample_1_output,
            "sample_2_input": exercise.sample_2_input,
            "sample_2_output": exercise.sample_2_output,
            "sample_3_input": exercise.sample_3_input,
            "sample_3_output": exercise.sample_3_output,
            "code": exercise.code,
            "exercise_difficulty": exercise.exercise_difficulty,
            "added_by_user_id": exercise.added_by_user_id,
            "score": exercise.score,
        }

        for i in range(1, 4):
            if exercise_dict[f"sample_{i}_output"]:
                exercise_dict[f"sample_{i}_output"] = (exercise_dict[f"sample_{i}_output"]
                                                       .decode("utf-8"))

        exercise_dicts.append(exercise_dict)

    return exercise_dicts


def decode_team_logo(top_scores):
    decoded_scores = []
    for score in top_scores:
        if score[3]:
            score = list(score)
            score[3] = score[3].decode("utf-8")
            decoded_scores.append(tuple(score))
        else:
            decoded_scores.append(score)
    return decoded_scores


def download_exercises():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    user_directory = os.path.join("users", username)

    if os.path.exists(user_directory):
        try:
            archive_name = f"{username}.tar.gz"
            with tarfile.open(archive_name, "w:gz") as tar:
                tar.add(user_directory, arcname=username)

            response = send_from_directory(".", archive_name, as_attachment=True)
            os.remove(archive_name)

            return response
        except Exception as e:
            flash(f"Failed to create, send, or delete archive: {str(e)}", "danger")
    else:
        flash("You have not submitted any solutions yet.", "warning")

    return redirect(url_for("user_profile"))


def exercise_app():
    if "username" not in session:
        return redirect(url_for("login"))

    page = request.args.get('page', 1, type=int)
    items_per_page = 10

    search_query = request.args.get('query', '')
    language = request.args.get('lang', 'python3')

    exercises = Exercise.query.filter(
        or_(
            Exercise.title.ilike(f"%{search_query}%"),
            Exercise.description.ilike(f"%{search_query}%")
        )
    ).order_by(Exercise.id.desc()).paginate(
        page=page,
        per_page=items_per_page,
        error_out=False
    )

    if search_query:
        for ex in exercises.items:
            ex.title = re.sub(search_query, "<mark>" + search_query + "</mark>",
                              ex.title, flags=re.IGNORECASE)
            ex.description = re.sub(search_query, "<mark>" + search_query + "</mark>",
                                    ex.description, flags=re.IGNORECASE)

    # exercises = fetch_exercises_from_database()

    for exercise in exercises.items:
        exercise.description = exercise.description.split("\n")[0]

        if exercise.user.team_id:
            exercise.user.team = Team.query.filter_by(id=exercise.user.team_id).first()
        tmp = get_top_scores(exercise.id, language)
        rank = []
        for score in tmp:
            if score[0]:
                rank.append(score[0])
        exercise.rank = rank

    top_scores = get_all_top_scores(language)

    top_daily_scores = get_all_daily_top_scores(language)

    return render_template("exercise/list.html", query=search_query,
                           exercises=exercises, top_daily_scores=top_daily_scores,
                           top_scores=top_scores)


def add_exercise():
    if "username" not in session:
        return redirect(url_for("login"))

    result = {}
    ex = {}

    if request.method == "POST":
        action = request.form.get("action")
        title = request.form["title"]
        description = request.form["description"]

        sample_inputs = {}
        sample_outputs = {}

        for i in range(1, 4):
            sample_inputs[f"sample_{i}_input"] = request.form.get(
                f"sample_{i}_input", None
            )
            sample_outputs[f"sample_{i}_output"] = request.form.get(
                f"sample_{i}_output", None
            )

        language = request.form.get("language", "python3")
        exercise_difficulty = request.form["difficulty"]
        username = session.get("username", None)
        user_id = User.query.filter_by(username=username).first().id

        if exercise_difficulty == "Easy":
            insert_difficulty = DifficultyEnum.Easy
            score = 10
        elif exercise_difficulty == "Medium":
            insert_difficulty = DifficultyEnum.Medium
            score = 20
        elif exercise_difficulty == "Hard":
            insert_difficulty = DifficultyEnum.Hard
            score = 30

        ex = {
            "title": title,
            "description": description,
            "exercise_difficulty": exercise_difficulty,
            "added_by_user_id": user_id,
            "score": score,
        }

        for key in sample_inputs:
            if sample_inputs[key]:
                sample_inputs[key] = sample_inputs[key].replace("\r\n", "\n")
                if sample_inputs[key][-1] != "\n":
                    sample_inputs[key] += "\n"
                ex[key] = sample_inputs[key]

        for key in sample_outputs:
            if sample_outputs[key]:
                sample_outputs[key] = sample_outputs[key].replace("\r\n", "\n")
                if sample_outputs[key][-1] != "\n":
                    sample_outputs[key] += "\n"
                ex[key] = sample_outputs[key]

        if action == "save":
            code = "# Write your code here"

            new_exercise = Exercise(
                title=title,
                description=description,
                sample_1_input=ex.get("sample_1_input", None),
                sample_1_output=ex.get("sample_1_output", None),
                sample_2_input=ex.get("sample_2_input", None),
                sample_2_output=ex.get("sample_2_output", None),
                sample_3_input=ex.get("sample_3_input", None),
                sample_3_output=ex.get("sample_3_output", None),
                code=code,
                exercise_difficulty=insert_difficulty,
                added_by_user_id=user_id,
                score=score,
            )

            for i in range(1, 4):
                if new_exercise.__dict__[f"sample_{i}_output"]:
                    new_exercise.__dict__[f"sample_{i}_output"] = (new_exercise.__dict__[f"sample_{i}_output"]
                                                                   .encode("utf-8"))

            db.session.add(new_exercise)
            db.session.commit()

            return redirect(url_for("exercise", exercise_id=new_exercise.id))

        elif action == "run":
            code = request.form["code"]
            ex["code"] = code
            ex["language"] = language
            result, _ = run_exercise(ex, 0, code)

    return render_template("/exercise/create.html", result=result, exercise=ex)


def check_login():
    if "username" not in session:
        return False
    return True


def save_user_code(username, exercise_id, user_code, language):
    user_directory = os.path.join("users", username)
    os.makedirs(user_directory, exist_ok=True)

    if language == "python3":
        file_name = f"{exercise_id}.py3"
    elif language == "go":
        file_name = f"{exercise_id}.go"
    else:
        file_name = f"{exercise_id}.py3"

    file_path = os.path.join(user_directory, file_name)

    with open(file_path, "w") as file:
        file.write(user_code)

    return file_path


def get_user_code(username, exercise_id, language):
    if language == "python3":
        file_path = os.path.join("users", username, f"{exercise_id}.py3")
    elif language == "go":
        file_path = os.path.join("users", username, f"{exercise_id}.go")
    else:
        file_path = os.path.join("users", username, f"{exercise_id}.py3")

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()

    return None


def execute_benchmark_inside_container(language, file_path, stdin=None):
    current_dir = os.getcwd()
    container_file_path = os.path.join("/", os.path.basename(file_path))
    host_file_path = os.path.join(current_dir, file_path)

    if language == "python3":
        image_name = "python:3.11"
        benchmark_file_path = os.path.join("/", "benchmark.py")
        host_benchmark_file_path = os.path.join(current_dir, "benchmark.py")
    elif language == "go":
        image_name = "golang:1.21"
        benchmark_file_path = os.path.join("/", "benchmark.go")
        host_benchmark_file_path = os.path.join(current_dir, "benchmark.go")

    command = [
        "podman",
        "run",
        "--rm",
        "-v",
        f"{host_benchmark_file_path}:{benchmark_file_path}",
        "-v",
        f"{host_file_path}:{container_file_path}",
        "-i",
        image_name,
        language,
        benchmark_file_path,
        container_file_path,
    ]

    try:
        if stdin:
            bytes_stdin = stdin.encode("utf-8")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(input=bytes_stdin, timeout=10)
        else:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout = b""
        stderr = b"Timeout expired"

    return stdout.decode("utf-8"), stderr.decode("utf-8")


def execute_inside_container(language, file_path, stdin=None):
    current_dir = os.getcwd()
    container_file_path = os.path.join("/", os.path.basename(file_path))
    host_file_path = os.path.join(current_dir, file_path)

    if language == "python3":
        image_name = "python:3.11"
    elif language == "go":
        image_name = "golang:1.21"
    else:
        language = "python3"
        image_name = "python:3.11"

    command = [
        "podman",
        "run",
        "--rm",
        "-v",
        f"{host_file_path}:{container_file_path}",
        "-i",
        image_name,
    ]

    if language == "python3":
        command.append(language)
        command.append(container_file_path)
    elif language == "go":
        command.append(language)
        command.append("run")
        command.append(container_file_path)

    try:
        if stdin:
            bytes_stdin = stdin.encode("utf-8")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate(input=bytes_stdin, timeout=10)
        else:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout = b""
        stderr = b"Timeout expired"

    return stdout.decode("utf-8"), stderr.decode("utf-8")


def execute_subprocess(command, cwd=None, stdin=None, timeout=10):
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            universal_newlines=True,
        )
        timer = Timer(timeout, process.kill)
        timer.start()
        if stdin:
            stdout, stderr = process.communicate(input=stdin)
        else:
            stdout, stderr = process.communicate()
        return stdout, stderr
    except Exception as e:
        return None, str(e)
    finally:
        timer.cancel()


def execute_benchmark_and_validate(ex, file_path, user_code):
    sample_inputs = ["sample_1_input", "sample_2_input", "sample_3_input"]
    sample_outputs = ["sample_1_output", "sample_2_output", "sample_3_output"]
    execution_time = []
    for input_key, output_key in zip(sample_inputs, sample_outputs):
        if input_key in ex and output_key in ex:
            if ex[input_key] is not None and ex[output_key] is not None:
                stdin = ex[input_key]
                expected_output = ex[output_key]
                stdout, stderr = execute_benchmark_inside_container(
                    ex["language"], file_path, stdin=stdin
                )
                execution_time.append(float(stdout))
            elif ex[output_key] is not None:
                expected_output = ex[output_key]
                stdout, stderr = execute_benchmark_inside_container(ex["language"], file_path)
                execution_time.append(float(stdout))
        elif output_key in ex:
            if ex[output_key] is not None:
                expected_output = ex[output_key]
                stdout, stderr = execute_benchmark_inside_container(ex["language"], file_path)
                execution_time.append(float(stdout))

    average_execution_time = sum(execution_time) / len(execution_time)
    return average_execution_time


def execute_and_validate(ex, file_path, user_code):
    result = {"type": "", "message": "", "stdout": "", "stderr": ""}

    sample_inputs = ["sample_1_input", "sample_2_input", "sample_3_input"]
    sample_outputs = ["sample_1_output", "sample_2_output", "sample_3_output"]

    for input_key, output_key in zip(sample_inputs, sample_outputs):
        if input_key in ex and output_key in ex:
            if ex[input_key] is not None and ex[output_key] is not None:
                stdin = ex[input_key]
                expected_output = ex[output_key]
                stdout, stderr = execute_inside_container(
                    ex["language"], file_path, stdin=stdin
                )
            elif ex[output_key] is not None:
                expected_output = ex[output_key]
                stdout, stderr = execute_inside_container(ex["language"], file_path)
        elif output_key in ex:
            if ex[output_key] is not None:
                expected_output = ex[output_key]
                stdout, stderr = execute_inside_container(ex["language"], file_path)

        if stdout != expected_output:
            result["type"] = "danger"
            result["message"] = "Your code is incorrect. Please try again."
            result["stdout"] = stdout
            result["stderr"] = stderr
            ex["code"] = user_code
            return result
        else:
            result["stdout"] = stdout
            result["stderr"] = stderr

    return result


def delete_exercise(exercise_id):
    if request.method == "POST":
        username = session["username"]
        user_id = User.query.filter_by(username=username).first().id

        exercise = Exercise.query.filter_by(id=exercise_id, added_by_user_id=user_id).first()

        if exercise:
            db.session.delete(exercise)
            db.session.commit()

            scores = ExerciseScore.query.filter_by(exercise_id=exercise_id).all()
            for score in scores:
                db.session.delete(score)
                db.session.commit()

            flash("Successfully deleted.", "success")

    return redirect(url_for("exercise_app"))


def run_exercise(ex, exercise_id, user_code):
    username = session["username"]
    language = ex["language"]
    file_path = save_user_code(username, exercise_id, user_code, language)
    top_scores = get_top_scores(exercise_id, language)

    if language == "python3":
        mypy_error_count, stdout_mypy = run_command(["mypy", "--strict", file_path])

        black_error, stdout_black = run_command(["black", "--check", "--diff", file_path])
        black_error = 1 if stdout_black else 0

        pylint_error, stdout_pylint = run_command(
            ["pylint", "--disable=C0103", "--score=no", file_path]
        )

        flake8_error_count, stdout_flake8 = run_command(["flake8", file_path])

    result = execute_and_validate(ex, file_path, user_code)

    if result["type"] == "danger":
        return result, top_scores

    benchmark_time = execute_benchmark_and_validate(ex, file_path, user_code)
    benchmark_time = round(benchmark_time, 4)

    ex["code"] = user_code

    total_score = ex["score"]

    if language == "python3":
        total_score, result = adjust_score_and_results(
            total_score,
            mypy_error_count,
            black_error,
            pylint_error,
            flake8_error_count,
            result,
            stdout_mypy,
            stdout_black,
            stdout_pylint,
            stdout_flake8,
            ex["score"]
        )
    else:
        total_score, result = adjust_score_and_results(
            total_score,
            0,
            0,
            0,
            0,
            result,
            "",
            "",
            "",
            "",
            ex["score"]
        )

    if total_score < ex["score"]:
        result["type"] = "warning"
    else:
        result["type"] = "success"

    result["message"] = "That is correct!"

    user = User.query.filter_by(username=username).first()

    if exercise_id != 0:
        total_score, result = update_user_score(
            user, language, exercise_id, total_score, result, benchmark_time
        )

    if total_score == ex["score"]:
        result["full_score"] = True

    result["message"] += f' You have earned {total_score}/{ex["score"]} points!'
    top_scores = get_top_scores(exercise_id, language)

    return result, top_scores


def run_command(command):
    stdout, stderr = execute_subprocess(command)
    error_count = len(stderr.splitlines())
    return error_count, stdout


def adjust_score_and_results(
    total_score,
    mypy_error_count,
    black_error,
    pylint_error,
    flake8_error_count,
    result,
    stdout_mypy,
    stdout_black,
    stdout_pylint,
    stdout_flake8,
    ex_score
):
    if mypy_error_count > 0:
        total_score -= mypy_error_count
        result["mypy"] = stdout_mypy
    if flake8_error_count > 0:
        total_score -= flake8_error_count
        result["flake8"] = stdout_flake8
    if black_error > 0:
        total_score -= black_error
        result["black"] = stdout_black
    if pylint_error > 0:
        total_score -= pylint_error
        result["pylint"] = stdout_pylint

    if total_score < ex_score:
        result["type"] = "warning"
    else:
        result["type"] = "success"

    return total_score, result


def update_user_score(user, language, exercise_id, total_score, result, benchmark_time):
    score = ExerciseScore.query.filter_by(user_id=user.id, exercise_id=exercise_id, language=language).first()

    if score:
        if total_score > score.total_score or benchmark_time < score.execution_time:
            result["message"] += " New record!"

        score.total_score = total_score
        score.execution_time = benchmark_time
    else:
        score = ExerciseScore(user_id=user.id, language=language, exercise_id=exercise_id, total_score=total_score,
                              execution_time=benchmark_time)

    db.session.add(score)
    db.session.commit()

    return total_score, result


def get_top_scores(exercise_id, language):
    try:
        top_scores = (
            db.session.query(
                User.username.label("username"),
                db.func.sum(ExerciseScore.total_score).label("total_score"),
                db.func.max(ExerciseScore.date_created).label("date_created"),
                Team.logo.label("logo"),
                db.func.sum(ExerciseScore.execution_time).label("execution_time"),
            )
            .join(ExerciseScore, User.id == ExerciseScore.user_id)
            .join(Team, User.team_id == Team.id, isouter=True)
            .filter(ExerciseScore.exercise_id == exercise_id)
            .filter(ExerciseScore.language == language)
            .group_by(User.username, Team.logo)
            .order_by(db.desc("total_score"), "execution_time")
            .all()
        )

        return top_scores

    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_all_daily_top_scores(language):
    try:
        top_scores = (
            db.session.query(
                User.username,
                db.func.sum(ExerciseScore.total_score).label('total_score'),
                db.func.max(ExerciseScore.date_created).label('date_created'),
                Team.logo,
                db.func.sum(ExerciseScore.execution_time).label('execution_time')
            )
            .outerjoin(ExerciseScore, User.id == ExerciseScore.user_id)
            .outerjoin(Team, User.team_id == Team.id)
            .filter(ExerciseScore.date_created >= db.func.date('now', '-1 day'))
            .filter(ExerciseScore.language == language)
            .group_by(User.username, Team.logo)
            .order_by(db.desc('total_score'), 'execution_time')
            .all()
        )

        return top_scores

    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_all_top_scores(language):
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
            .filter(ExerciseScore.language == language)
            .group_by(User.username, Team.logo)
            .order_by(db.desc('total_score'), 'execution_time')
            .having(db.func.sum(ExerciseScore.total_score) > 0)
            .all()
        )

        return top_scores

    except Exception as e:
        print(f"Database error: {e}")
        return []


def exercise(exercise_id):
    if not check_login():
        return redirect(url_for("login"))

    user = user_utils.get_user_by_username(session["username"])
    exercises = fetch_exercises_from_database()

    ex = find_exercise_by_id(exercises, exercise_id)
    if ex is None:
        return render_template("/exercise/404.html", user=user)

    num_of_exercises = len(exercises)
    language = request.args.get('lang', 'python3')

    if request.method == "POST":
        description = request.form.get("description", None)
        if description:
            ex["description"] = description
            exercise = Exercise.query.filter_by(id=exercise_id).first()
            user = User.query.filter_by(username=session["username"]).first()
            if user.id != exercise.added_by_user_id:
                flash("You are not allowed to edit this exercise", "danger")
                return redirect(url_for("exercise", exercise_id=exercise_id))

            exercise.description = description
            db.session.commit()
            flash("Description updated successfully", "success")
            return redirect(url_for("exercise", exercise_id=exercise_id))

        user_code = request.form["code"]
        ex["language"] = language
        result, top_scores = run_exercise(ex, exercise_id, user_code)
        return render_template(
            "/exercise/exercise.html",
            exercise=ex,
            user=user,
            num_of_exercises=num_of_exercises,
            result=result,
            top_scores=top_scores,
        )

    user_code = get_user_code(user.username, exercise_id, language)

    if user_code:
        ex["code"] = user_code
        print(user_code)

    top_scores = get_top_scores(exercise_id, language)

    return render_template(
        "/exercise/exercise.html",
        exercise=ex,
        user=user,
        num_of_exercises=num_of_exercises,
        result={},
        top_scores=top_scores,
    )


def find_exercise_by_id(exercises, exercise_id):
    return next((e for e in exercises if e["id"] == exercise_id), None)
