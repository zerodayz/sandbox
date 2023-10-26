import os

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for, send_from_directory)

from models import User
from apps.ctf import fetch_ctfs_from_database, find_ctf_by_id, update_team_score, get_top_scores


def challenge_complete(ctf_id, user, ex):
    total_score = ex["score"]
    result = {"type": "success", "message": "That is correct!", "stdout": "", "stderr": "",
              "next_text": ex['next_text'], "next_password": ex['next_password'], "full_score": True}

    total_score, result = update_team_score(
        user.team_id, ctf_id, total_score, result
    )

    result["message"] += f' Your team have earned {total_score} points!'
    top_scores = get_top_scores(ctf_id)

    return result, top_scores


def challenge_failed(ctf_id):
    result = {"type": "danger", "message": "That is not the correct solution.", "stdout": "", "stderr": ""}
    top_scores = get_top_scores(ctf_id)

    return result, top_scores


def challenge_checksum():
    ctf_id = 16
    username = session["username"]
    user = User.query.filter_by(username=username).first()
    ctfs = fetch_ctfs_from_database()
    num_of_ctfs = len(ctfs)
    ex = find_ctf_by_id(ctfs, ctf_id)

    if request.method == "POST":
        a0 = int(request.form.get("a0", None))
        a1 = int(request.form.get("a1", None))
        a2 = int(request.form.get("a2", None))
        a3 = int(request.form.get("a3", None))
        a4 = int(request.form.get("a4", None))
        a5 = int(request.form.get("a5", None))
        a6 = int(request.form.get("a6", None))
        a7 = int(request.form.get("a7", None))
        a8 = int(request.form.get("a8", None))
        array = [a0, a1, a2, a3, a4, a5, a6, a7, a8]
        if None in array:
            result, top_scores = challenge_failed(16)
            return render_template(
                "/ctf/ctf.html",
                ctf=ex,
                user=user,
                num_of_ctfs=num_of_ctfs,
                result=result,
                top_scores=top_scores,
            )

        poly = [1, 3, 17, 37, 127, 127, 131, 5, 47, 1]
        sum = 1
        for i in range(0, 8):
            sum *= poly[i]
            sum += array[i]
            i += 1
        if (sum % 10) == array[8]:
            result, top_scores = challenge_complete(16, user, ex)
        else:
            result, top_scores = challenge_failed(16)

        return render_template(
            "/ctf/ctf.html",
            ctf=ex,
            user=user,
            num_of_ctfs=num_of_ctfs,
            result=result,
            top_scores=top_scores,
        )