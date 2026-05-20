from app.config.database import db


class TelegramNotification(db.Model):

    __tablename__ = "telegram_notifications"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    schedule_id = db.Column(
        db.Integer,
        db.ForeignKey("schedules.id", ondelete="SET NULL"),
        nullable=True
    )

    notification_type = db.Column(
        db.String(50),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=True
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )

    sent_at = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    error_message = db.Column(
        db.Text,
        nullable=True
    )

    __table_args__ = (
        db.Index("idx_telegram_notification_user", "user_id"),
        db.Index("idx_telegram_notification_schedule", "schedule_id"),
        db.Index("idx_telegram_notification_status", "status"),
        db.Index(
            "idx_telegram_notification_once",
            "schedule_id",
            "notification_type"
        ),
    )
