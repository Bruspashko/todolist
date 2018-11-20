from flask_jwt_extended import (jwt_required, get_jwt_identity)
from flask import (
    Blueprint, request, jsonify
)
from todolist.db import get_db

bp = Blueprint('tasks', __name__, url_prefix='/tasks')
@bp.route('/', methods=['GET'])
@jwt_required
def getAllTasks():
  db = get_db()
  user_id = get_jwt_identity()
  tasks = db.execute('SELECT * FROM task WHERE user_id = ?', (user_id,)).fetchall()
  task_list = list()
  for task in tasks:
    task_list.append(dict(task))
  return jsonify({"tasks": task_list}), 200

@bp.route('/', methods=['POST'])
@jwt_required
def createTask():
  db = get_db()
  user_id = get_jwt_identity()
  if not request.json['title']:
      error = 'Title is required.'
  elif not request.json['body']:
      error = 'Body is required.'
        
  db.execute(
    'INSERT INTO task (user_id, title, body) VALUES (?, ?, ?)',
    (user_id,request.json['title'], request.json['body'])
  )
  db.commit()
  last_row_id = db.execute('SELECT last_insert_rowid()').fetchone()
  task = db.execute('SELECT * FROM task WHERE id = ?', (last_row_id["last_insert_rowid()"],)).fetchone()
  print(task)
  return jsonify(dict(task)), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required
def getTask(id):
  db = get_db()
  user_id = get_jwt_identity()
  error = None
  task = db.execute('SELECT * FROM task WHERE user_id = ? AND id = ?', (user_id,id)).fetchone()
  if task is None:
    error = "This task doesn't exist"
  if error is None:
    return jsonify(dict(task)), 200
  return jsonify({'error': True, 'message': error}), 401

@bp.route('/<int:id>', methods=['DELETE'])
@jwt_required
def deleteTask(id):
  db = get_db()
  user_id = get_jwt_identity()
  error = None
  task = db.execute('SELECT * FROM task WHERE user_id = ? AND id = ?', (user_id,id)).fetchone()
  if task is None:
    error = "This task doesn't exist"
  if error is None:
    db.execute('DELETE FROM task WHERE user_id = ? AND id = ?', (user_id,id))
    db.commit()
    return jsonify({"success": True}), 200
  return jsonify({'error': True, 'message': error}), 401

@bp.route('/<int:id>', methods=['PUT'])
@jwt_required
def editTask(id):
  db = get_db()
  user_id = get_jwt_identity()
  error = None
  if not request.json['title']:
      error = 'Title is required.'
  elif not request.json['body']:
      error = 'Body is required.'
  task = db.execute('SELECT * FROM task WHERE user_id = ? AND id = ?', (user_id,id)).fetchone()
  if task is None:
    error = "This task doesn't exist"
  if error is None:
    db.execute('UPDATE task SET title = ?, body = ?WHERE user_id = ? AND id = ?', (request.json['title'],request.json['body'],user_id,id))
    db.commit()
    task = db.execute('SELECT * FROM task WHERE user_id = ? AND id = ?', (user_id,id)).fetchone()
    return jsonify(dict(task)), 200
  return jsonify({'error': True, 'message': error}), 401

