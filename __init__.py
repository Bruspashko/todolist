import os
from flask import Flask
from flask_jwt_extended import JWTManager

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'todolist.sqlite'),
    )
    app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'
    jwt = JWTManager(app)
    from . import db
    db.init_app(app)
    
    from todolist.resource import auth
    app.register_blueprint(auth.bp)
  
    from todolist.resource import tasks
    app.register_blueprint(tasks.bp)
  
      
    return app