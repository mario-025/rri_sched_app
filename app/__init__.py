from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from werkzeug.serving import is_running_from_reloader
from app.config.database import db
from app.config.settings import Config
from app.config.limiter import limiter
import logging
import os
import datetime
from dotenv import load_dotenv

# Import all models to register them with SQLAlchemy
from app.models import Shift, ShiftPattern, ShiftPatternDetail, Schedule, User, Admin
from app.routes.home_routes import home_bp
from app.routes.schedule_routes import schedule_bp
from app.routes.user_routes import user_bp
from app.routes.user_profile_routes import user_profile_bp
from app.routes.shift_routes import shift_bp
from app.routes.shift_pattern_routes import shift_pattern_bp
from app.routes.auth_routes import auth
from app.bot_manager import start_bot_thread
from app.services.telegram_notifier import start_notifier_thread

# Load environment variables
load_dotenv()

def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["TELEGRAM_BOT_TOKEN"] = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Database configuration - support both Docker and local
    # Docker: DB_HOST=mysql (service name)
    # Local: DB_HOST=localhost
    db_host = os.getenv('DB_HOST', os.getenv('DATABASE_HOST', 'localhost'))
    db_port = os.getenv('DB_PORT', os.getenv('DATABASE_PORT', '3306'))
    db_user = os.getenv('DB_USER', os.getenv('DATABASE_USER', 'root'))
    db_password = os.getenv('DB_PASSWORD', os.getenv('DATABASE_PASSWORD', ''))
    db_name = os.getenv('DB_NAME', os.getenv('DATABASE_NAME', 'rritmb'))
    
    # Build database URI
    if db_password:
        database_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    else:
        database_uri = f"mysql+pymysql://{db_user}@{db_host}:{db_port}/{db_name}"
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Apply engine options (pool configuration, connection timeout, etc)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.SQLALCHEMY_ENGINE_OPTIONS
    
    # Session config
    app.config["SECRET_KEY"] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    
    # Setup logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
    
    db.init_app(app)
    limiter.init_app(app)

    @app.before_request
    def enforce_admin_timeout_before_request():
        from app.controllers.auth_controller import enforce_admin_session_timeout

        return enforce_admin_session_timeout()
        
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found"""
        app.logger.warning(f'404 Error: {error}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handle 405 Method Not Allowed without showing generic 500."""
        app.logger.warning(f'405 Error: {error}')
        flash('Aksi tidak valid. Silakan gunakan tombol/form yang tersedia.', 'warning')
        return redirect(request.referrer or url_for('home.home'))
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f'500 Error: {error}', exc_info=True)
        try:
            db.session.rollback()
        except:
            pass
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_all_exceptions(error):
        """Catch ALL exceptions (database, operational, etc) and show generic error"""
        # Log detailed error server-side untuk debugging
        app.logger.error(f'Exception: {type(error).__name__}: {str(error)}', exc_info=True)
        
        # Rollback database session
        try:
            db.session.rollback()
        except:
            pass
        
        # Show generic 500 error page (NO sensitive info to user)
        return render_template('errors/500.html'), 500
    
    # ====== REGISTER BLUEPRINTS ======
    app.register_blueprint(auth)
    app.register_blueprint(home_bp)
    app.register_blueprint(
        schedule_bp,
        url_prefix="/schedules"
    )
    app.register_blueprint(
        user_bp,
        url_prefix="/users"
    )
    app.register_blueprint(user_profile_bp)
    app.register_blueprint(shift_bp)
    app.register_blueprint(shift_pattern_bp)
    
    # ====== INITIALIZE TELEGRAM VERIFICATION STORAGE ======
    app.pending_telegram_verifications = {}
    
    # ====== START TELEGRAM BOT (if token available) ======
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_enabled = os.getenv('TELEGRAM_BOT_ENABLED', 'true').lower() == 'true'
    use_reloader = os.getenv('FLASK_USE_RELOADER', 'false').lower() == 'true'
    should_start_bot = (
        telegram_enabled
        and telegram_token
        and (
            os.getenv('FLASK_ENV', 'production') != 'development'
            or not use_reloader
            or is_running_from_reloader()
        )
    )

    if should_start_bot:
        try:
            start_bot_thread(telegram_token)
            app.logger.info("Telegram bot thread started")
            start_notifier_thread(app, telegram_token)
            app.logger.info("Telegram schedule notifier thread started")
        except Exception as e:
            app.logger.error(f"Failed to start telegram bot: {e}")
    elif telegram_token and telegram_enabled:
        app.logger.info("Telegram bot skipped in Flask reloader parent process")
    elif telegram_token:
        app.logger.info("Telegram bot disabled by TELEGRAM_BOT_ENABLED")
    else:
        app.logger.warning("TELEGRAM_BOT_TOKEN not found in .env - Bot disabled")

    # ====== HEALTH CHECK ENDPOINT ======
    @app.route('/health')
    def health_check():
        """Health check endpoint untuk Docker & monitoring systems"""
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            return jsonify({
                'status': 'healthy',
                'service': 'sched-app',
                'database': 'connected',
                'timestamp': datetime.datetime.utcnow().isoformat()
            }), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503

    return app
