from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from enum import Enum as EnumBase, unique

from sqlalchemy import Index, MetaData

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


@unique
class DifficultyEnum(EnumBase):
    Easy = 'Easy'
    Medium = 'Medium'
    Hard = 'Hard'

    def __str__(self):
        return self.value


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    last_login = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    last_login_ip = db.Column(db.String)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    team = db.relationship('Team', back_populates='members')

    def __repr__(self):
        return str(self.__dict__)

    __table_args__ = (
        Index('idx_username', 'username'),
    )


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    hashed_password = db.Column(db.String, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    members = db.relationship('User', back_populates='team')
    logo = db.Column(db.BLOB)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return str(self.__dict__)

    __table_args__ = (
        Index('idx_team_id', 'id'),
    )


class TeamInvitation(db.Model):
    __tablename__ = 'team_invitations'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return str(self.__dict__)

    __table_args__ = (
        Index('idx_team_invitation_id', 'id'),
    )


class Ctf(db.Model):
    __tablename__ = 'ctfs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.BLOB)
    solution = db.Column(db.String)
    ctf_password = db.Column(db.String)
    next_password = db.Column(db.String)
    next_text = db.Column(db.String)
    code = db.Column(db.String)
    ctf_difficulty = db.Column(db.Enum(DifficultyEnum), nullable=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    sample_1_input = db.Column(db.Text)
    sample_1_output = db.Column(db.BLOB)
    sample_2_input = db.Column(db.Text)
    sample_2_output = db.Column(db.BLOB)
    sample_3_input = db.Column(db.Text)
    sample_3_output = db.Column(db.BLOB)
    code = db.Column(db.Text)
    language = db.Column(db.String)
    exercise_difficulty = db.Column(db.Enum(DifficultyEnum), nullable=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    __table_args__ = (
        Index('idx_exercise_id', 'id'),
    )


class ExerciseScore(db.Model):
    __tablename__ = 'exercise_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)
