#!/bin/bash

export FLASK_ENV=production
export FLASK_APP=app.py

flask run --host=0.0.0.0 --port=8080