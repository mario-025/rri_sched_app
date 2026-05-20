from app.config.database import db

class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    fullname = db.Column(
        db.String(100),
        nullable=False
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    phone_number = db.Column(
        db.String(15),
        nullable=True
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    password = db.Column(
        db.String(255),
        nullable=True
    )

    score = db.Column(
        db.Integer,
        default=0
    )

    # Telegram fields
    telegram_id = db.Column(
        db.String(50),
        unique=True,
        nullable=True
    )

    telegram_username = db.Column(
        db.String(100),
        nullable=True
    )

    telegram_enabled = db.Column(
        db.Boolean,
        default=False
    )

    telegram_verified = db.Column(
        db.Boolean,
        default=False
    )

    telegram_verified_at = db.Column(
        db.DateTime,
        nullable=True
    )

    schedules = db.relationship("Schedule", back_populates="user")