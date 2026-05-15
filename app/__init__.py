from flask import Flask
from app.config.database import db
from app.config.settings import Config
# Import all models to register them with SQLAlchemy
from app.models import Shift, ShiftPattern, ShiftPatternDetail, Schedule, User
from app.routes.schedule_routes import schedule_bp
from app.routes.user_routes import user_bp

def create_app():

    app = Flask(__name__)
    app.config.from_object(Config)
    

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+pymysql://root:@localhost/rritmb"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    app.register_blueprint(
        schedule_bp,
        url_prefix="/schedules"
    )
    app.register_blueprint(
        user_bp,
        url_prefix="/users"
    )
    

    return app