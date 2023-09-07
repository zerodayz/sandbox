import uuid
import os

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for, send_from_directory)


def serve_uploaded_file(filename):
    return send_from_directory('uploads', filename)


def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file was uploaded."})

        file = request.files["file"]

        os.makedirs("uploads", exist_ok=True)
        file_name = str(uuid.uuid4())

        file.save(os.path.join("uploads", file_name))

        return jsonify({"success": True, "message": "File uploaded successfully.", "filename": file_name})
