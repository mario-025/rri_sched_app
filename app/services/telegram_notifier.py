import datetime
import atexit
import logging
import os
import threading
from zoneinfo import ZoneInfo

import requests
from sqlalchemy.exc import SQLAlchemyError

from app.config.database import db
from app.models.schedule import Schedule
from app.models.telegram_notification import TelegramNotification
from app.models.user import User


logger = logging.getLogger(__name__)


class TelegramScheduleNotifier:
    """Background scheduler untuk reminder jadwal lewat Telegram."""

    def __init__(self, app, token):
        self.app = app
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.stop_event = threading.Event()
        self.interval_seconds = int(os.getenv("TELEGRAM_NOTIFIER_INTERVAL", "30"))
        timezone_name = os.getenv("APP_TIMEZONE", "Asia/Makassar")
        self.timezone = ZoneInfo(timezone_name)

    def stop(self):
        self.stop_event.set()

    def run(self):
        logger.info("Telegram schedule notifier started")
        with self.app.app_context():
            self._ensure_table()

        while not self.stop_event.is_set():
            try:
                with self.app.app_context():
                    self.process_due_notifications()
            except Exception as e:
                logger.error(f"Telegram notifier error: {e}", exc_info=True)

            self.stop_event.wait(self.interval_seconds)

        logger.info("Telegram schedule notifier stopped")

    def _ensure_table(self):
        try:
            TelegramNotification.__table__.create(db.engine, checkfirst=True)
        except SQLAlchemyError as e:
            logger.error(f"Failed to ensure telegram_notifications table: {e}")

    def process_due_notifications(self):
        now = datetime.datetime.now(self.timezone).replace(second=0, microsecond=0)

        due_items = []
        due_items.extend(self._fixed_time_due_items(now))
        due_items.extend(self._before_shift_due_items(now))

        for schedule, notification_type in due_items:
            self._send_once(schedule, notification_type)

    def _fixed_time_due_items(self, now):
        items = []

        if now.hour == 22 and now.minute == 0:
            tomorrow = now.date() + datetime.timedelta(days=1)
            items.extend(
                (schedule, "reminder_1day")
                for schedule in self._active_schedules_for_date(tomorrow)
            )

        if now.hour == 7 and now.minute == 0:
            today = now.date()
            items.extend(
                (schedule, "reminder_today_7am")
                for schedule in self._active_schedules_for_date(today)
            )

        return items

    def _before_shift_due_items(self, now):
        items = []
        target_dates = {
            now.date(),
            now.date() + datetime.timedelta(days=1),
        }

        schedules = (
            Schedule.query
            .join(User, Schedule.user_id == User.id)
            .filter(
                Schedule.work_date.in_(target_dates),
                User.telegram_id.isnot(None),
                User.telegram_verified.is_(True),
                User.telegram_enabled.is_(True),
            )
            .all()
        )

        for schedule in schedules:
            start_at = datetime.datetime.combine(
                schedule.work_date,
                schedule.shift.start_time,
                tzinfo=self.timezone
            ).replace(second=0, microsecond=0)

            if now == start_at - datetime.timedelta(minutes=10):
                items.append((schedule, "reminder_10min"))

            if now == start_at - datetime.timedelta(minutes=5):
                items.append((schedule, "reminder_5min"))

        return items

    def _active_schedules_for_date(self, work_date):
        return (
            Schedule.query
            .join(User, Schedule.user_id == User.id)
            .filter(
                Schedule.work_date == work_date,
                User.telegram_id.isnot(None),
                User.telegram_verified.is_(True),
                User.telegram_enabled.is_(True),
            )
            .all()
        )

    def _send_once(self, schedule, notification_type):
        already_attempted = TelegramNotification.query.filter_by(
            schedule_id=schedule.id,
            notification_type=notification_type
        ).first()

        if already_attempted:
            return

        title, message = self._build_message(schedule, notification_type)
        notification = TelegramNotification(
            user_id=schedule.user_id,
            schedule_id=schedule.id,
            notification_type=notification_type,
            title=title,
            message=message,
            status="pending"
        )
        db.session.add(notification)
        db.session.flush()

        try:
            result = self._send_message(schedule.user.telegram_id, message)
            if result.get("ok"):
                notification.status = "sent"
                notification.sent_at = datetime.datetime.now()
                logger.info(
                    f"Telegram notification sent: schedule={schedule.id}, "
                    f"type={notification_type}"
                )
            else:
                notification.status = "failed"
                notification.error_message = str(result)
                logger.warning(f"Telegram notification failed: {result}")
        except Exception as e:
            notification.status = "failed"
            notification.error_message = str(e)
            logger.error(f"Telegram send error: {e}")

        db.session.commit()

    def _send_message(self, chat_id, text):
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10
        )
        return response.json()

    def _build_message(self, schedule, notification_type):
        shift = schedule.shift
        work_date = schedule.work_date.strftime("%d %b %Y")
        time_range = (
            f"{shift.start_time.strftime('%H:%M')} - "
            f"{shift.end_time.strftime('%H:%M')}"
        )

        if notification_type == "reminder_1day":
            title = "Reminder jadwal besok"
            intro = "Besok Anda memiliki jadwal kerja."
        elif notification_type == "reminder_today_7am":
            title = "Reminder jadwal hari ini"
            intro = "Hari ini Anda memiliki jadwal kerja."
        elif notification_type == "reminder_10min":
            title = "Reminder 10 menit sebelum shift"
            intro = "Shift Anda akan dimulai dalam 10 menit."
        else:
            title = "Reminder 5 menit sebelum shift"
            intro = "Shift Anda akan dimulai dalam 5 menit."

        message = f"""
<b>{title}</b>

Halo {schedule.user.fullname},
{intro}

<b>Shift:</b> {shift.shift_name}
<b>Waktu:</b> {time_range}
<b>Tanggal:</b> {work_date}
<b>Jenis Jadwal:</b> {schedule.schedule_type}
        """.strip()

        return title, message


notifier_thread = None
notifier_instance = None
notifier_lock = threading.Lock()


def start_notifier_thread(app, token):
    global notifier_thread, notifier_instance

    with notifier_lock:
        if notifier_thread is not None and notifier_thread.is_alive():
            logger.info("Telegram schedule notifier already running")
            return

        notifier_instance = TelegramScheduleNotifier(app, token)
        notifier_thread = threading.Thread(
            target=notifier_instance.run,
            name="telegram-schedule-notifier",
            daemon=True
        )
        notifier_thread.start()


def stop_notifier_thread():
    global notifier_thread, notifier_instance

    with notifier_lock:
        if notifier_instance is not None:
            notifier_instance.stop()

        if notifier_thread is not None and notifier_thread.is_alive():
            notifier_thread.join(timeout=10)

        notifier_thread = None
        notifier_instance = None


atexit.register(stop_notifier_thread)
