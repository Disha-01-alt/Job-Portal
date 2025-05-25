import os
import logging
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload settings
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directories exist
upload_dirs = ['uploads/cvs', 'uploads/id_cards', 'uploads/marksheets']
for directory in upload_dirs:
    os.makedirs(directory, exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'google_auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.candidate_routes import candidate_bp
from routes.admin_routes import admin_bp
from routes.company_routes import company_bp
from google_auth import google_auth

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(candidate_bp, url_prefix='/candidate')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(company_bp, url_prefix='/company')
app.register_blueprint(google_auth)

# Import database initialization
from database import init_db

# Initialize database
with app.app_context():
    init_db()

# Import auth setup
from auth import setup_auth
setup_auth(login_manager)

# Main routes
from flask import render_template, redirect, url_for
from flask_login import current_user

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'candidate':
            return redirect(url_for('candidate_routes.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_routes.dashboard'))
        elif current_user.role == 'company':
            return redirect(url_for('company_routes.dashboard'))
    return render_template('index.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html', content='<div class="container"><h1>Page Not Found</h1><p>The page you are looking for does not exist.</p></div>'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', content='<div class="container"><h1>Internal Server Error</h1><p>An unexpected error occurred. Please try again later.</p></div>'), 500
