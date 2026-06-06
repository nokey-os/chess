from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Game(db.Model):
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True)
    white_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    black_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    result = db.Column(db.String(10), default='*')
    game_type = db.Column(db.String(10), nullable=False)
    fen = db.Column(db.String(100), default=STARTING_FEN)
    status = db.Column(db.String(10), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    white_player = db.relationship('User', foreign_keys=[white_user_id], backref='games_as_white')
    black_player = db.relationship('User', foreign_keys=[black_user_id], backref='games_as_black')
