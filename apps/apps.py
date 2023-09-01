import os
import sqlite3
import subprocess
from threading import Timer
from typing import Any

from flask import (flash, jsonify, redirect, render_template, request, session,
                   url_for)

import user as user_utils
import utils.constants as constants

DB_NAME = constants.DB_NAME


def fetch_exercises_from_database(
    database_name: str = DB_NAME,
) -> list[dict[str, Any]]:
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM exercises")
        exercise_rows = cursor.fetchall()

        exercises = []
        for row in exercise_rows:
            exercise = {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "sample_1_input": row[3],
                "sample_1_output": row[4],
                "sample_2_input": row[5],
                "sample_2_output": row[6],
                "sample_3_input": row[7],
                "sample_3_output": row[8],
                "code": row[9],
                "language": row[10],
                "difficulty": row[11],
                "added_by": row[12],
                "score": row[13],
            }
            exercises.append(exercise)

    return exercises


def exercise_app():
    if "username" not in session:
        return redirect(url_for("login"))

    exercises: list[dict[str, Any]] = fetch_exercises_from_database()
    top_scores = get_all_top_scores()

    return render_template("exercise/list.html", exercises=exercises, top_scores=top_scores)


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

        language = request.form["language"]
        difficulty = request.form["difficulty"]
        added_by = session.get("username", None)

        if difficulty == "easy":
            score = 10
        elif difficulty == "medium":
            score = 20
        elif difficulty == "hard":
            score = 30

        ex = {
            "title": title,
            "description": description,
            "language": language,
            "difficulty": difficulty,
            "added_by": added_by,
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
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            insert_data = (
                title,
                description,
                ex.get("sample_1_input", None),
                ex.get("sample_1_output", None),
                ex.get("sample_2_input", None),
                ex.get("sample_2_output", None),
                ex.get("sample_3_input", None),
                ex.get("sample_3_output", None),
                code,
                language,
                difficulty,
                added_by,
                score,
            )

            insert_query = """
                INSERT INTO exercises (
                    title, description, sample_1_input, sample_1_output,
                    sample_2_input, sample_2_output, sample_3_input, sample_3_output,
                    code, language, difficulty, added_by, score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(insert_query, insert_data)
            exercise_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return redirect(url_for("exercise", exercise_id=exercise_id))

        elif action == "run":
            code = request.form["code"]
            ex["code"] = code
            result, _ = run_exercise(ex, 0, code)

    return render_template("/exercise/create.html", result=result, exercise=ex)


def check_login():
    if "username" not in session:
        return False
    return True


def save_user_code(username, exercise_id, user_code):
    user_directory = os.path.join("users", username)
    os.makedirs(user_directory, exist_ok=True)

    file_name = f"{exercise_id}.py3"
    file_path = os.path.join(user_directory, file_name)

    with open(file_path, "w") as file:
        file.write(user_code)

    return file_path


def get_user_code(username, exercise_id):
    file_path = os.path.join("users", username, f"{exercise_id}.py3")

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()

    return None


def execute_inside_container(language, file_path, stdin=None):
    current_dir = os.getcwd()
    container_file_path = os.path.join("/", os.path.basename(file_path))
    host_file_path = os.path.join(current_dir, file_path)

    if language == "python3":
        image_name = "python:3.11"
    else:
        raise ValueError("Unsupported language")

    command = [
        "podman",
        "run",
        "--rm",
        "-v",
        f"{host_file_path}:{container_file_path}",
        "-i",
        image_name,
        language,
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
        user_id = session["username"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM exercises WHERE id = ? AND added_by = ?",
                (exercise_id, user_id),
            )

            cursor.execute("DELETE FROM scores WHERE exercise_id = ?", (exercise_id,))

            conn.commit()

        flash("Successfully deleted.", "success")

    return redirect(url_for("exercise_app"))


def run_exercise(ex, exercise_id, user_code):
    username = session["username"]
    file_path = save_user_code(username, exercise_id, user_code)
    top_scores = get_top_scores(exercise_id)

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

    ex["code"] = user_code

    total_score = ex["score"]
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
        ex["score"],
        ex,
        username,
        exercise_id,
    )

    if total_score < ex["score"]:
        result["type"] = "warning"
    else:
        result["type"] = "success"

    result["message"] = "That is correct!"

    if exercise_id != 0:
        total_score, result = update_user_score(
            username, exercise_id, total_score, ex["score"], result
        )

    if total_score == ex["score"]:
        result["full_score"] = True

    result["message"] += f' You have earned {total_score}/{ex["score"]} points!'
    top_scores = get_top_scores(exercise_id)

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
    ex_score,
    ex,
    username,
    exercise_id,
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


def update_user_score(username, exercise_id, total_score, ex_score, result):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT total_score
            FROM scores
            WHERE username=? AND exercise_id=?
            """,
            (username, exercise_id),
        )
        score = cursor.fetchone()

        if score:
            if total_score > score[0]:
                result["message"] += " New record!"
                cursor.execute(
                    """
                    UPDATE scores
                    SET total_score=?
                    WHERE username=? AND exercise_id=?
                    """,
                    (total_score, username, exercise_id),
                )
        else:
            cursor.execute(
                """
                INSERT INTO scores (username, exercise_id, total_score)
                VALUES (?, ?, ?)
                """,
                (username, exercise_id, total_score),
            )

        connection.commit()

    return total_score, result


def get_top_scores(exercise_id):
    with sqlite3.connect(DB_NAME) as connection:
        cursor = connection.cursor()

        query = """
            SELECT s.username, s.total_score, s.date_created, t.logo
            FROM scores s
            JOIN users u ON s.username = u.username
            LEFT JOIN teams t ON u.team = t.id
            WHERE s.exercise_id = ?
            ORDER BY s.total_score DESC;
        """
        cursor.execute(query, (exercise_id,))
        top_scores = cursor.fetchall()

    return top_scores


def get_all_top_scores():
    try:
        with sqlite3.connect(DB_NAME) as connection:
            cursor = connection.cursor()

            query = """
                SELECT s.username, SUM(s.total_score) AS total_score, MAX(s.date_created) AS date_created, t.logo
                FROM scores s
                JOIN users u ON s.username = u.username
                LEFT JOIN teams t ON u.team = t.id
                GROUP BY s.username
                ORDER BY total_score DESC;
            """

            cursor.execute(query)
            top_scores = cursor.fetchall()

            return top_scores

    except sqlite3.Error as e:
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

    if request.method == "POST":
        user_code = request.form["code"]
        result, top_scores = run_exercise(ex, exercise_id, user_code)
        return render_template(
            "/exercise/exercise.html",
            exercise=ex,
            user=user,
            num_of_exercises=num_of_exercises,
            result=result,
            top_scores=top_scores,
        )

    print(f"{user.username} is opening... {exercise_id}")
    user_code = get_user_code(user.username, exercise_id)

    if user_code:
        ex["code"] = user_code
        print(user_code)

    top_scores = get_top_scores(exercise_id)
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
