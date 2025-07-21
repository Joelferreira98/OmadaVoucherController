import os
import logging
import pymysql
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
# Load environment variables from .env file manually
def load_env_file():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass

load_env_file()

# Install PyMySQL as MySQLdb
pymysql.install_as_MySQLdb()

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
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Fallback for development - use SQLite
    database_url = "sqlite:///voucher_app.db"
    logging.info("Using SQLite database fallback")
    
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure CSRF exemptions for API routes
@csrf.exempt
def exempt_api_routes():
    # Exempt API routes from CSRF protection
    api_routes = ['/api/sync-sites', '/api/sync-vouchers', '/api/sync-status']
    return request.endpoint and any(route in request.path for route in api_routes)

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
