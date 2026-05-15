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

    score = db.Column(
        db.Integer,
        default=0
    )

    schedules = db.relationship("Schedule", back_populates="user")