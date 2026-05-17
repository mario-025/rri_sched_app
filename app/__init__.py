from flask import Flask, render_template
from app.config.database import db
from app.config.settings import Config
import logging

# Import all models to register them with SQLAlchemy
from app.models import Shift, ShiftPattern, ShiftPatternDetail, Schedule, User, Admin
from app.routes.home_routes import home_bp
from app.routes.schedule_routes import schedule_bp
from app.routes.user_routes import user_bp
from app.routes.user_profile_routes import user_profile_bp
from app.routes.shift_routes import shift_bp
from app.routes.shift_pattern_routes import shift_pattern_bp
from app.routes.auth_routes import auth

def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://root:@localhost/rritmb"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Apply engine options (pool configuration, connection timeout, etc)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = Config.SQLALCHEMY_ENGINE_OPTIONS
    
    # Session config
    app.config["SECRET_KEY"] = "your-secret-key-change-this-in-production"
    app.config["SESSION_COOKIE_SECURE"] = False  # Set True in production with HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    
    # Setup logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
    
    db.init_app(app)
    
    # ====== ERROR HANDLERS (Register FIRST before blueprints) ======
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found"""
        app.logger.warning(f'404 Error: {error}')
        return render_template('errors/404.html'), 404
    
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

    return app