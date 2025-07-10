import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

with app.app_context():
    # Import models to create tables
    import models
    db.create_all()
    
    # Create default master user if not exists
    from models import User
    from werkzeug.security import generate_password_hash
    
    master = User.query.filter_by(username='master').first()
    if not master:
        master = User(
            username='master',
            email='master@system.com',
            password_hash=generate_password_hash('admin123'),
            user_type='master',
            is_active=True
        )
        db.session.add(master)
        db.session.commit()
        logging.info("Master user created: username=master, password=admin123")
