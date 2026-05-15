from app.config.database import db

class Shift(db.Model):

    __tablename__ = "shifts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    shift_index = db.Column(
        db.Integer,
        nullable=False
    )

    shift_name = db.Column(
        db.String(100),
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    score = db.Column(
        db.Integer,
        default=1
    )
    
    pattern_details = db.relationship(
        "app.models.shift_patern_detail.ShiftPatternDetail",
        back_populates="shift"
    )