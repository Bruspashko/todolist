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
from . import db
db.init_app(app
```

