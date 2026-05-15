from app.config.database import db


class ShiftPatternDetail(db.Model):

    __tablename__ = (
        "shift_pattern_details"
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    pattern_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "shift_patterns.id"
        )
    )

    shift_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "shifts.id"
        )
    )

    worker_count = db.Column(
        db.Integer
    )

    pattern = db.relationship(
        "ShiftPattern",
        back_populates="details"
    )

    shift = db.relationship(
        "app.models.shift.Shift",
        back_populates="pattern_details"
    )