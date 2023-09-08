from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    team_invitation = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    team = db.relationship('Team', back_populates='members', foreign_keys=[team_id])
    last_login = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    last_login_ip = db.Column(db.String)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return str(self.__dict__)


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    members = db.relationship('User', back_populates='team', foreign_keys=[User.team_id])
    logo = db.Column(db.BLOB)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return str(self.__dict__)


class Ctf(db.Model):
    __tablename__ = 'ctfs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    description = db.Column(db.BLOB)
    solution = db.Column(db.String)
    password = db.Column(db.String)
    next_password = db.Column(db.String)
    next_text = db.Column(db.String)
    code = db.Column(db.String)
    difficulty = db.Column(db.String)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)


class CtfScore(db.Model):
    __tablename__ = 'ctf_scores'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    ctf_id = db.Column(db.Integer, db.ForeignKey('ctfs.id'), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)


class Exercise(db.Model):
    __tablename__ = 'exercises'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    description = db.Column(db.String)
    sample_1_input = db.Column(db.String)
    sample_1_output = db.Column(db.BLOB)
    sample_2_input = db.Column(db.String)
    sample_2_output = db.Column(db.BLOB)
    sample_3_input = db.Column(db.String)
    sample_3_output = db.Column(db.BLOB)
    code = db.Column(db.String)
    language = db.Column(db.String)
    difficulty = db.Column(db.String)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)


class ExerciseScore(db.Model):
    __tablename__ = 'exercise_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)
