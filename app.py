import os
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session
import chess
from models import db, User, Game, STARTING_FEN


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24).hex()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chess.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'flask_session')
    app.config['SESSION_PERMANENT'] = False

    db.init_app(app)
    Session(app)

    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        db.create_all()

    return app


app = create_app()


PROMO_MAP = {'q': chess.QUEEN, 'r': chess.ROOK, 'b': chess.BISHOP, 'n': chess.KNIGHT}


def load_board(fen=None):
    try:
        return chess.Board(fen or STARTING_FEN)
    except ValueError:
        return chess.Board()


def finish_game(game, board):
    outcome = board.outcome()
    if outcome is None:
        game.result = '1/2-1/2'
    elif outcome.winner == chess.WHITE:
        game.result = '1-0'
    else:
        game.result = '0-1'
    game.status = 'finished'


# ─── Auth ────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            flash('Введите имя пользователя')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── Main ────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    session.pop('game_id', None)
    session.pop('board_fen', None)
    session.pop('game_type', None)

    users = User.query.filter(User.id != user.id).order_by(User.username).all()
    recent_games = Game.query.order_by(Game.created_at.desc()).limit(10).all()

    return render_template('index.html', user=user, users=users, recent_games=recent_games)


@app.route('/play/<game_type>', methods=['GET', 'POST'])
def play_game(game_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if game_type not in ('bot', 'human'):
        flash('Некорректный тип игры')
        return redirect(url_for('index'))

    user = db.session.get(User, session['user_id'])

    if game_type == 'bot':
        game = Game(white_user_id=user.id, game_type='bot', status='active')
    else:
        if request.method == 'POST':
            opponent_id = request.form.get('opponent_id')
            if not opponent_id:
                flash('Выберите соперника')
                return redirect(url_for('index'))
            opponent = db.session.get(User, int(opponent_id))
            if not opponent or opponent.id == user.id:
                flash('Некорректный соперник')
                return redirect(url_for('index'))
            game = Game(
                white_user_id=user.id,
                black_user_id=opponent.id,
                game_type='human',
                status='active',
            )
        else:
            flash('Выберите соперника на главной')
            return redirect(url_for('index'))

    db.session.add(game)
    db.session.commit()
    session['game_id'] = game.id
    session['board_fen'] = STARTING_FEN
    session['game_type'] = game_type

    return render_template('game.html', game=game, fen=STARTING_FEN)


@app.route('/lobby')
def lobby():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    waiting = Game.query.filter(
        Game.game_type == 'human',
        Game.status == 'waiting',
        Game.white_user_id != session['user_id'],
    ).all()
    return render_template('lobby.html', games=waiting)


@app.route('/game/<int:game_id>/join', methods=['POST'])
def join_game(game_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    game = db.session.get(Game, game_id)
    if not game or game.game_type != 'human' or game.status != 'waiting':
        flash('Нельзя присоединиться к этой игре')
        return redirect(url_for('lobby'))
    if game.white_user_id == session['user_id']:
        flash('Нельзя играть самому с собой')
        return redirect(url_for('lobby'))

    game.black_user_id = session['user_id']
    game.status = 'active'
    db.session.commit()

    session['game_id'] = game.id
    session['board_fen'] = game.fen or STARTING_FEN
    session['game_type'] = game.game_type
    return redirect(url_for('index'))


# ─── Game play ───────────────────────────────────────────────

@app.route('/move', methods=['POST'])
def move():
    if 'user_id' not in session:
        return {'error': 'Не авторизован'}, 401

    game_id = session.get('game_id')
    fen = session.get('board_fen')
    if not game_id or not fen:
        return {'error': 'Нет активной игры'}, 400

    game = db.session.get(Game, game_id)
    if not game or game.status != 'active':
        return {'error': 'Игра не активна'}, 400

    data = request.get_json(force=True)
    from_sq = chess.parse_square(data.get('from'))
    to_sq = chess.parse_square(data.get('to'))
    promo = PROMO_MAP.get(data.get('promotion'))

    board = load_board(fen)
    move_obj = chess.Move(from_sq, to_sq)
    if move_obj not in board.legal_moves and promo:
        move_obj = chess.Move(from_sq, to_sq, promotion=promo)
    if move_obj not in board.legal_moves:
        return {'error': 'Недопустимый ход'}, 400

    board.push(move_obj)
    session['board_fen'] = board.fen()
    db.session.commit()

    resp = {
        'fen': board.fen(),
        'game_over': board.is_game_over(),
        'winner': None,
        'check': board.is_check(),
    }

    if board.is_game_over():
        outcome = board.outcome()
        resp['winner'] = None if outcome.winner is None else ('w' if outcome.winner == chess.WHITE else 'b')
        finish_game(game, board)
        game.fen = board.fen()
        db.session.commit()
        session.pop('board_fen', None)
        return resp

    if game.game_type == 'bot' and not board.is_game_over():
        bot_move = random.choice(list(board.legal_moves))
        board.push(bot_move)
        session['board_fen'] = board.fen()
        resp['fen'] = board.fen()
        resp['check'] = board.is_check()

        if board.is_game_over():
            outcome = board.outcome()
            resp['winner'] = None if outcome.winner is None else ('w' if outcome.winner == chess.WHITE else 'b')
            resp['game_over'] = True
            finish_game(game, board)
            game.fen = board.fen()
            db.session.commit()
            session.pop('board_fen', None)
        else:
            game.fen = board.fen()
            db.session.commit()

    return resp


@app.route('/resign', methods=['POST'])
def resign():
    if 'user_id' not in session:
        return {'error': 'Не авторизован'}, 401

    game_id = session.get('game_id')
    if not game_id:
        return {'error': 'Нет активной игры'}, 400

    game = db.session.get(Game, game_id)
    if not game or game.status != 'active':
        return {'error': 'Игра не активна'}, 400

    user_id = session['user_id']

    if game.white_user_id == user_id:
        game.result = '0-1'
        winner = 'b'
    elif game.black_user_id == user_id:
        game.result = '1-0'
        winner = 'w'
    else:
        return {'error': 'Вы не участник игры'}, 400

    game.status = 'finished'
    db.session.commit()
    session.pop('board_fen', None)

    board = load_board(game.fen)
    return {
        'fen': board.fen(),
        'game_over': True,
        'winner': winner,
        'check': False,
    }


if __name__ == '__main__':
    app.run(debug=True)
