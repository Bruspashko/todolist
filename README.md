# todolist
This tutorial will walk you thru creating a simple CRUD application with RESTful interface. Particularly we will be creating a simple to-do list for authneticated users.

We will design total of 7 endpoints. 

| Type  | Endpoint | Function |
| ------------- | ------------- | ------------- |
| POST  | `/auth/register` | Register a User | 
| POST | `/auth/login`  | Login as a User |
| GET | `/tasks/`  | Get all tasks |
| POST | `/tasks/`  | Create a new taks |
| GET | `/tasks/<task_id>`  | Get task by task ID |
| PUT | `/tasks/<task_id>`  | Update task |
| DELETE | `/tasks/<task_id>`  | Delete task |

 ### File structure of application

    .
    ├── __init__.py              # Application factory file
    ├── db.py                    # Database client
    ├── schema.sql               # SQL for DB init
    ├── .gitignore               # Git ignore
    └── resource                 # Resource folder that will contain all resources
          ├── auth.py            # Auth resource 
          └── task.py            # Task resource


## Code development
### Application Factory
Application factory `__init__.py` is the initial file that will create an object of application. It contains all app level configurations as well as processes that should be executed during application launch.
Here is the base code for our app factory
```
import os
from flask import Flask

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
      
    return app
```

As you can see this file will import two packages: `os` and `flask`. Os is a default python package which doesn't require us installing it. 
In case with flask, we will have to install flask package. To do so we will run the following command: `pip install flask`
This will install flask package and make it global for us to use anywhere.

In function create_app we have argument test_config, but we would not need to use that configuration file in current application. 
Function create_app will be automatically picked up by flask and executed on the intialization. 
In function we will basically create a Flask class and return it. 

### Database connection and initialization

Create file `db.py` 

```
import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()
     
def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
    
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
```

Libraries needed: 

`sqlite3` - DB-API interface for SQLite databases

`click` - package to design CLI commands for application

`flask` - framework modules

Function explanation:

`get_db()` - open db connection

`close_db(e)` - close db connection

`init_db()` - will read sql script and execute it, needed to setup up db table schema or purge data

`init_db_command()` - has two decorators: 
* `@click.command('init-db')` - declare the CLI command `init-db` that will allow to run sql script to setup db
* `@with_appcontext` - guarentees to execute the function with app context

`init_app(app)` - function that will add `init-db` command to list of available CLI commands. 

We need to add `init_app` in our factory class so it's executed on every app initialization. Please add this code to `__init__.py` before `return app`
```
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'todolist.sqlite'),
)
from . import db
db.init_app(app)
```

Create `schema.sql`

This is SQL script that will setup table schema. 

```
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS task;

CREATE TABLE user (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  status INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES user (id)
);
```
### Auth resource 
As we are done on the infrastructure side. We have Database client interface, we have table schema mapped, and we have factory class that will initialize the application. As was mentioned before, our application will have basic auth to todo tasks can be created by multiple users. In this case we will create auth resource that will do login and registration.

Create file `resource/auth.py` with the following content: 

```
from flask import (
    Blueprint, request, jsonify, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from todolist.db import get_db
from flask_jwt_extended import (create_access_token, jwt_required, get_jwt_identity)
```
__Packages used:__
 
`flask` - framework packages

`werkzeug.security` - package to generate and check password hash. We will use it to generate password has on registration and check that hash on login. 

`todolist.db` - our db client interface. We will be using to get access to database to run quaries.

`flask_jwt_extended` - package for basic HTTP Auth. JWT stands for JSON Web Tokens. We will be using it to generate tokens on login that will be used on client side to access `tasks` resource. 

Run the following command in CLI to install `flask_jwt_extended` package 

```
pip install flask-jwt-extended
```

Let's register Blueprint. Blueprint is a way to organize your application in a smaller re-usable peaces. We will store our route endpoints for auth resource in blueprint. 

```
bp = Blueprint('auth', __name__, url_prefix='/auth')
```

This means that auth blueprint will have routes that will start with prefix /auth. 
Lets register `/register` route that will be used to register a user

```
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
```

`@bp.route` decorator is used to define the route for the endpoint. 

We will first check if JSON object contains all needed properties, which are `usertname` and `password`, and also check if a user with this username already exists. 

If user doesn't exists we will proceed with inserting a record in the table with password hashed by using `generate_password_hash` function 

We will return user information and ID in JSON format. We will use `jsonify` for it. 

All errors will be return with HTTP 400 code and the following payload:

```
{
 "error": True,
 "message": "...."
}
```

Lets register `/login` route that will be used to authorize. Endpoint will return authorization token that will be used in `tasks` resource. 

```
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
    return jsonify({'error': True, 'message': error}), 401
```

We will check if `username` is found in database. If it is, we will use `check_password_hash` to verify if password is correct

We will then use `create_access_token` to generate token for the user. First argument contains user_id, it is used to reference user id in other resources. For second argument it is a delta expiration time of the token. For this application we will use tokens that never expire, but it is recomended to use Authorization Token and Refresh Token. Authorization token expires usually expires in short time and refresh token has longer expiration time. Refresh Token is used to get Authorization token when it expired. 

We will then return token in JSON format inside `token` property.


### Task resource 

Task resource will contain Blueprint with 5 routes.
* Get all Tasks 
* Create a new task
* Get Task by id
* Edit task by id 
* Delete task by id 

Let's create a new file `resource/tasks.py`, and add all dependencies that we will use in this module. 

```

from flask_jwt_extended import (jwt_required, get_jwt_identity)
from flask import (
    Blueprint, request, jsonify
)
from todolist.db import get_db
```

We are already familiar with all packages we will be using, so let's get into defining the blue print

`bp = Blueprint('tasks', __name__, url_prefix='/tasks')`

We will now register the first route which will be used to get all tasks

```
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
```

As you can see we are using two decorators here. 
*`@bp.route` to register a route `/` and it should expect GET method
*`@jwt_required` to specify that this function requires Authorization token to be included and valid, otherwise it will return 401 HTTP error which states for "Unauthorized" 

Inside function we will use `get_jwt_identity()` which will return us user id, which we can then use for our SQL query to get list of all tasks. 

jsonify will then prepare the string and we will return array of objects 

Most of the other code in this module is pretty similar so here it is:

```
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
  return jsonify({'error': True, 'message': error}), 404

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
  return jsonify({'error': True, 'message': error}), 404

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
  return jsonify({'error': True, 'message': error}), 404
```

The only thing to notice here is the decorators for the endpoint of individual resources. 
For example 
```
@bp.route('/<int:id>', methods=['PUT'])
@jwt_required
def editTask(id):
``` 

As you can see first argument in the `@bp.route` decorator is `/<int:id>` and function has one argument `id`, this would allow us to pass task id into the function from the route that will look something like this. `/tasks/1` that means that we would like to edit task with ID: 1. 


### JWT Manager Configuration

For JWT to work properly we need to add configurations in our factory class. First import jwt package
```
from flask_jwt_extended import JWTManager
```
After this add the following code before `return app`

```
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
jwt = JWTManager(app)
```
This will create an object of JWTManager class as well as set `JWT_SECRET_KEY` in application configuration. 


### Register Blueprints

As we are done with our resources it's now time to register blueprints. 

To do so add the following code before `return app` in `__init__.py`

```
from todolist.resource import auth
app.register_blueprint(auth.bp)

from todolist.resource import tasks
app.register_blueprint(tasks.bp)
```

## Application Launch

To launch the application we need to add some env variables first.  
```
export FLASK_APP=todolist
```
Now we have to create a database. To do so we will use `init-db` command that we registered in the beginning of the tutorial

```
flask init-db
```

We will be running this application on CodeAnyWhere platform so we will be listening on port 3000, this is what CodeAnywhere uses for HTTPS.

```
flask run --host=0.0.0.0 --port=3000
```
Now you should have web server listening on port 3000. 

## Testing

We will be using CURL CLI client to test our application. To start we will register our new user using `/auth/register` endpoint. 

Here is code for CURL command:
```
curl -X POST \
  <server_url>/auth/register \
  -H 'accept: application/json' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
  "username": "user",
  "password": "password"
}'
```

The response from server should look like this:
```
{
    "id": 15,
    "password": "password",
    "username": "user"
}
```

This means we succesfully registered a new user. 

The next step is to login and obtain our authorization token:

```
curl -X POST \
  <server_url>/auth/login \
  -H 'accept: application/json' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
  "username": "user",
  "password": "password"
}'
```

And the response should look like this 

```
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss"
}
```

To access `/tasks` resource we would have to use this token and it should be in our Authorization header. 

Lets try to get all our tasks now. 

```
curl -X GET \
  <server_url>/tasks/ \
  -H 'accept: application/json' \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json'
}'
```

As you can see our `Authorization` header contains string that start with `Bearer` followed by the token we received when we logged in. 

As we currently don't have any tasks for our user, the response you should expect is this:

```
{
    "tasks": []
}
```

Let's create a new task now by running the following request:

```
curl -X POST \
  <server_url>/tasks/ \
  -H 'accept: application/json' \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
  "title": "Cook Dinner",
  "body": "Buy Pizza and no cooking! "
}'
```

The response we should get should be simillar to this: 

```
{
    "body": "Buy Pizza and no cooking! ",
    "created": "Tue, 20 Nov 2018 03:48:20 GMT",
    "id": 7,
    "status": 0,
    "title": "Cook Dinner",
    "user_id": 15
}
```

Let's modify our task by running PUT request: 
```
curl -X PUT \
  <server_url>/tasks/7 \
  -H 'accept: application/json' \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json' \
  -d '{
  "title": "Cook Dinner",
  "body": "Should I get sushi instead? "
}'
```
The reponse is: 

```
{
    "body": "Should I get sushi instead? ",
    "created": "Tue, 20 Nov 2018 03:48:20 GMT",
    "id": 7,
    "status": 0,
    "title": "Cook Dinner",
    "user_id": 15
}
```


To get task with ID 7 we should run the following request

```

curl -X GET \
  <server_url>/tasks/7 \
  -H 'accept: application/json' \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json'
}'
```

The response we will get is this: 

```
{
    "body": "Should I get sushi instead? ",
    "created": "Tue, 20 Nov 2018 03:48:20 GMT",
    "id": 7,
    "status": 0,
    "title": "Cook Dinner",
    "user_id": 15
}
```

And the last endpoint to test is DELETE request. 

To run it use the following request:
```
curl -X DELETE \
  <server_url>/tasks/7 \
  -H 'accept: application/json' \
  -H 'authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE1NDI2ODUzNzAsIm5iZiI6MTU0MjY4NTM3MCwianRpIjoiNmViZDQ3N2QtYmUyNS00NDViLTllY2EtMDA1NmExMDE1YmM1IiwiaWRlbnRpdHkiOjE1LCJmcmVzaCI6ZmFsc2UsInR5cGUiOiJhY2Nlc3MifQ.Sdr1m3GTaLuLLzPvDwka3zy_OrNvmM03CfOOjPeUHss' \
  -H 'cache-control: no-cache' \
  -H 'content-type: application/json'
}'
```

And the response is: 
```
{
    "success": true
}
```

__Please note: replace `<server_url>` with your server URL.__

Our application is now tested. Happy coding!
