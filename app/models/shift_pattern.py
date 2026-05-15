from app.config.database import db

class ShiftPattern(db.Model):

    __tablename__ = "shift_patterns"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    pattern_name = db.Column(
        db.String(100)
    )

    description = db.Column(
        db.Text
    )

    details = db.relationship(
        "app.models.shift_patern_detail.ShiftPatternDetail",
        back_populates="pattern"
    )