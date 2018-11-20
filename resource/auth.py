from flask_jwt_extended import (create_access_token, jwt_required, get_jwt_identity)
from flask import (
    Blueprint, request, jsonify, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from todolist.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')
@bp.route('/register', methods=['POST'])
def register():
    db = get_db()
    error = None

    if not request.json['username']:
        error = 'Username is required.'
    elif not request.json['password']:
        error = 'Password is required.'
    elif db.execute(
        'SELECT id FROM user WHERE username = ?', (request.json['username'],)
    ).fetchone() is not None:
        error = 'User {} is already registered.'.format(request.json['username'])
    if error is None:
        db.execute(
            'INSERT INTO user (username, password) VALUES (?, ?)',
            (request.json['username'], generate_password_hash(request.json['password']))
        )
        db.commit()
        last_row_id = db.execute('SELECT last_insert_rowid()').fetchone()
        request.json['id'] = last_row_id['last_insert_rowid()']
        return jsonify(request.json), 200
    return jsonify({'error': True, 'message': error}), 400
  
@bp.route('/login', methods=['POST'])
def login():
    db = get_db()
    error = None
    username = request.json['username']
    password = request.json['password']
    user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

    if user is None:
        error = 'Incorrect username.'
    elif not check_password_hash(user['password'], password):
        error = 'Incorrect password.'
        
    if error is None:
      token = create_access_token(user['id'], expires_delta=False)
      return jsonify({'token': token}), 200
    return jsonify({'error': True, 'message': error}), 400
         
