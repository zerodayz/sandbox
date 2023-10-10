#!/bin/bash

# export FLASK_ENV=production
# export FLASK_APP=app.py

# flask run --host=0.0.0.0 --port=8080

# prepare benchmark tool
go build -o benchmark benchmark.go
gunicorn --daemon -c gunicorn_config.py app:app
nginx -c $PWD/nginx.conf

