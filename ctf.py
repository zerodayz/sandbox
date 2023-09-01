from flask import render_template


def get_ctf():
    return render_template("ctf/ctf.html")
