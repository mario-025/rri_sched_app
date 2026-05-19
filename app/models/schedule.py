from app.config.database import db

class Schedule(db.Model):

    __tablename__ = "schedules"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    shift_id = db.Column(
        db.Integer,
        db.ForeignKey("shifts.id"),
        nullable=False
    )

    work_date = db.Column(
        db.Date,
        nullable=False
    )

    schedule_type = db.Column(
        db.String(100),
        nullable=False,
        default='broadcast',
        index=True
    )

    user = db.relationship(
        "User", 
        back_populates="schedules"
    )
    shift = db.relationship(
        "app.models.shift.Shift",
        foreign_keys=[shift_id],
        lazy="joined"
    )