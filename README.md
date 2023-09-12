# sandbox
Sandbox Application

![Sandbox](screenshots/sandbox_exercises_dark.png)
![Sandbox](screenshots/sandbox_exercises_light.png)

## Installation

```bash
$ git clone https://github.com/zerodayz/sandbox.git
$ cd sandbox
$ pip install -r requirements.txt
``` 

## Development

### Running the sandbox application locally

```bash
$ python3 app.py
```

## Production
### Requirements
- nginx
- podman (for running the sandbox containers)

```bash
$ sudo apt-get install nginx
$ sudo apt-get install podman
```

### Running the sandbox application in Production

There is a script that will run the sandbox application in gunicorn and nginx.
```bash
$ bash /run.sh
```
