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

# Konfigurasi reminder shift pegawai
# (menit_sebelum_shift, notification_type, judul, isi_intro)
BEFORE_SHIFT_REMINDER_CONFIG = [
    (24 * 60, "reminder_1day",    "Reminder 1 Hari Sebelum Shift",   "Besok Anda memiliki jadwal kerja."),
    (12 * 60, "reminder_12hours", "Reminder 12 Jam Sebelum Shift",   "Shift Anda dimulai 12 jam lagi."),
    (60,      "reminder_1hour",   "Reminder 1 Jam Sebelum Shift",    "Shift Anda akan dimulai dalam 1 jam."),
    (30,      "reminder_30min",   "Reminder 30 Menit Sebelum Shift", "Shift Anda akan dimulai dalam 30 menit."),
    (10,      "reminder_10min",   "Reminder 10 Menit Sebelum Shift", "Shift Anda akan dimulai dalam 10 menit."),
    (5,       "reminder_5min",    "Reminder 5 Menit Sebelum Shift",  "Shift Anda akan dimulai dalam 5 menit."),
]

# KONFIGURASI DIGEST JADWAL MINGGUAN
# Dikirim 2x sehari: pagi & malam — berisi semua jadwal 7 hari ke depan.
DIGEST_MORNING_HOUR   = int(os.getenv("DIGEST_MORNING_HOUR",   "7"))
DIGEST_MORNING_MINUTE = int(os.getenv("DIGEST_MORNING_MINUTE", "0"))
DIGEST_EVENING_HOUR   = int(os.getenv("DIGEST_EVENING_HOUR",   "21"))
DIGEST_EVENING_MINUTE = int(os.getenv("DIGEST_EVENING_MINUTE", "0"))
DIGEST_LOOKAHEAD_DAYS = int(os.getenv("DIGEST_LOOKAHEAD_DAYS", "7"))

DAY_NAMES_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


class TelegramScheduleNotifier:
    """Background scheduler untuk reminder jadwal lewat Telegram."""

    def __init__(self, app, token):
        self.app = app
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.stop_event = threading.Event()
        self.interval_seconds = int(os.getenv("TELEGRAM_NOTIFIER_INTERVAL", "30"))
        self.timezone = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Makassar"))

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

    # ENTRY POINT — dipanggil setiap interval
    def process_due_notifications(self):
        now = datetime.datetime.now(self.timezone).replace(second=0, microsecond=0)

        # 1. Digest jadwal mingguan (per user, 2x sehari)
        for user, notification_type, schedules in self._digest_due_items(now):
            self._send_digest_once(user, notification_type, schedules, now)

        # 2. Reminder per-shift (1 hari / 12 jam / 1 jam / 30 mnt / 10 mnt / 5 mnt)
        for schedule, notification_type in self._before_shift_due_items(now):
            self._send_schedule_once(schedule, notification_type)

    # Digest jadwal mingguan

    def _digest_due_items(self, now):
        """
        Periksa apakah sekarang waktunya kirim digest pagi atau malam.
        Return list of (user, notification_type, schedules).
        Hanya users yang punya jadwal dalam 7 hari ke depan yang diproses.
        """
        is_morning = (now.hour == DIGEST_MORNING_HOUR and now.minute == DIGEST_MORNING_MINUTE)
        is_evening = (now.hour == DIGEST_EVENING_HOUR and now.minute == DIGEST_EVENING_MINUTE)

        if not (is_morning or is_evening):
            return []

        # notification_type menyertakan tanggal agar idempoten per hari
        period = "pagi" if is_morning else "malam"
        notification_type = f"digest_{period}_{now.date()}"  # contoh: "digest_pagi_2024-01-15"

        users = User.query.filter(
            User.telegram_id.isnot(None),
            User.telegram_verified.is_(True),
            User.telegram_enabled.is_(True),
        ).all()

        start_date = now.date()
        end_date   = start_date + datetime.timedelta(days=DIGEST_LOOKAHEAD_DAYS - 1)

        items = []
        for user in users:
            schedules = (
                Schedule.query
                .filter(
                    Schedule.user_id == user.id,
                    Schedule.work_date >= start_date,
                    Schedule.work_date <= end_date,
                )
                .order_by(Schedule.work_date, Schedule.id)
                .all()
            )
            # Hanya kirim digest kalau user punya jadwal mendatang
            if schedules:
                items.append((user, notification_type, schedules))

        return items

    # Reminder per-shift
    def _before_shift_due_items(self, now):
        """
        Untuk setiap konfigurasi di BEFORE_SHIFT_REMINDER_CONFIG, cek apakah
        sekarang tepat waktunya mengirim reminder ke masing-masing user.
        Return list of (schedule, notification_type).
        """

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

        items = []
        for schedule in schedules:
            start_at = datetime.datetime.combine(
                schedule.work_date,
                schedule.shift.start_time,
                tzinfo=self.timezone,
            ).replace(second=0, microsecond=0)

            for minutes_before, notification_type, _, _ in BEFORE_SHIFT_REMINDER_CONFIG:
                trigger_at = start_at - datetime.timedelta(minutes=minutes_before)
                if now == trigger_at:
                    items.append((schedule, notification_type))

        return items

    # Digest jadwal mingguan (idempoten per user + tanggal + pagi/malam)
    def _send_digest_once(self, user, notification_type, schedules, now):
        """
        Kirim digest; skip jika sudah ada record untuk user + notification_type hari ini.
        Deduplication menggunakan (user_id, notification_type) karena schedule_id = NULL.
        """
        already = TelegramNotification.query.filter_by(
            user_id=user.id,
            notification_type=notification_type,
        ).first()

        if already:
            return

        title, message = self._build_digest_message(user, schedules, now)
        notification = TelegramNotification(
            user_id=user.id,
            schedule_id=None,
            notification_type=notification_type,
            title=title,
            message=message,
            status="pending",
        )
        db.session.add(notification)
        db.session.flush()

        try:
            result = self._send_message(user.telegram_id, message)
            if result.get("ok"):
                notification.status = "sent"
                notification.sent_at = datetime.datetime.now()
                logger.info(f"Digest sent: user={user.id}, type={notification_type}")
            else:
                notification.status = "failed"
                notification.error_message = str(result)
                logger.warning(f"Digest failed: user={user.id}, result={result}")
        except Exception as e:
            notification.status = "failed"
            notification.error_message = str(e)
            logger.error(f"Digest send error: user={user.id}, error={e}")

        db.session.commit()

    def send_manual_digest_to_all_users(self):
        """
        Kirim digest 7 hari ke depan ke semua user Telegram aktif.
        Dipakai oleh tombol admin, jadi tidak memakai dedup digest otomatis.
        """
        now = datetime.datetime.now(self.timezone).replace(second=0, microsecond=0)
        notification_type = f"manual_digest_{now.strftime('%Y%m%d%H%M%S')}"
        start_date = now.date()
        end_date = start_date + datetime.timedelta(days=DIGEST_LOOKAHEAD_DAYS - 1)

        users = User.query.filter(
            User.telegram_id.isnot(None),
            User.telegram_verified.is_(True),
            User.telegram_enabled.is_(True),
        ).all()

        sent_count = 0
        failed_count = 0

        for user in users:
            schedules = (
                Schedule.query
                .filter(
                    Schedule.user_id == user.id,
                    Schedule.work_date >= start_date,
                    Schedule.work_date <= end_date,
                )
                .order_by(Schedule.work_date, Schedule.id)
                .all()
            )

            title, message = self._build_digest_message(user, schedules, now)
            notification = TelegramNotification(
                user_id=user.id,
                schedule_id=None,
                notification_type=notification_type,
                title=title,
                message=message,
                status="pending",
            )
            db.session.add(notification)
            db.session.flush()

            try:
                result = self._send_message(user.telegram_id, message)
                if result.get("ok"):
                    notification.status = "sent"
                    notification.sent_at = datetime.datetime.now()
                    sent_count += 1
                else:
                    notification.status = "failed"
                    notification.error_message = str(result)
                    failed_count += 1
                    logger.warning(f"Manual digest failed: user={user.id}, result={result}")
            except Exception as e:
                notification.status = "failed"
                notification.error_message = str(e)
                failed_count += 1
                logger.error(f"Manual digest send error: user={user.id}, error={e}")

        db.session.commit()
        return {
            "users": len(users),
            "sent": sent_count,
            "failed": failed_count,
        }

    # Reminder per-shift (idempoten per schedule_id + notification_type)
    def _send_schedule_once(self, schedule, notification_type):
        """
        Kirim reminder shift; skip jika sudah pernah dikirim (atau dicoba).
        Deduplication dijamin oleh index idx_telegram_notification_once
        pada (schedule_id, notification_type).
        """
        already = TelegramNotification.query.filter_by(
            schedule_id=schedule.id,
            notification_type=notification_type,
        ).first()

        if already:
            return

        title, message = self._build_schedule_message(schedule, notification_type)
        notification = TelegramNotification(
            user_id=schedule.user_id,
            schedule_id=schedule.id,
            notification_type=notification_type,
            title=title,
            message=message,
            status="pending",
        )
        db.session.add(notification)
        db.session.flush()

        try:
            result = self._send_message(schedule.user.telegram_id, message)
            if result.get("ok"):
                notification.status = "sent"
                notification.sent_at = datetime.datetime.now()
                logger.info(
                    f"Schedule reminder sent: schedule={schedule.id}, "
                    f"type={notification_type}"
                )
            else:
                notification.status = "failed"
                notification.error_message = str(result)
                logger.warning(f"Schedule reminder failed: {result}")
        except Exception as e:
            notification.status = "failed"
            notification.error_message = str(e)
            logger.error(f"Schedule reminder send error: {e}")

        db.session.commit()

    # TELEGRAM API
    def _send_message(self, chat_id, text):
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return response.json()

    # PESAN: Digest jadwal mingguan
    def _build_digest_message(self, user, schedules, now):
        """
        Contoh output:
        ──────────────────────────────
        📅 Jadwal Kerja 7 Hari Ke Depan
        24 Jun – 30 Jun 2025

        Selamat pagi, Budi Santoso!
        Berikut jadwal kerja Anda minggu ini:

        📌 Senin, 24 Jun 2025
             Shift Pagi  |  06:00 - 14:00

        📌 Rabu, 26 Jun 2025
             Shift Siang  |  14:00 - 22:00
        ──────────────────────────────
        """
        greeting   = self._resolve_time_greeting(now)
        title      = f"📅 Jadwal Kerja {DIGEST_LOOKAHEAD_DAYS} Hari Ke Depan"
        end_date   = now.date() + datetime.timedelta(days=DIGEST_LOOKAHEAD_DAYS - 1)
        date_range = (
            f"{now.date().strftime('%d %b')} – {end_date.strftime('%d %b %Y')}"
        )

        lines = []
        for schedule in schedules:
            day_name   = DAY_NAMES_ID[schedule.work_date.weekday()]
            date_str   = schedule.work_date.strftime("%d %b %Y")
            time_range = self._format_time_range(schedule.shift)
            lines.append(
                f"📌 <b>{day_name}, {date_str}</b>\n"
                f"     {schedule.shift.shift_name}  |  {time_range}"
            )

        schedule_body = "\n\n".join(lines)
        if not schedule_body:
            schedule_body = f"Tidak ada jadwal kerja dalam {DIGEST_LOOKAHEAD_DAYS} hari ke depan."

        message = (
            f"<b>{title}</b>\n"
            f"<i>{date_range}</i>\n\n"
            f"{greeting}, <b>{user.fullname}</b>!\n"
            f"Berikut jadwal kerja Anda untuk {DIGEST_LOOKAHEAD_DAYS} hari ke depan:\n\n"
            f"{schedule_body}"
        )

        return title, message

    # PESAN: Reminder per-shift
    def _build_schedule_message(self, schedule, notification_type):
        """
        Contoh output (reminder_1hour):
        ──────────────────────────────
        🔔 Reminder 1 Jam Sebelum Shift

        Halo Budi Santoso,
        Shift Anda akan dimulai dalam 1 jam.

        Shift  : Shift Pagi
        Hari   : Senin, 24 Jun 2025
        Waktu  : 06:00 - 14:00
        Jenis  : Regular
        ──────────────────────────────
        """
        shift      = schedule.shift
        day_name   = DAY_NAMES_ID[schedule.work_date.weekday()]
        date_str   = schedule.work_date.strftime("%d %b %Y")
        time_range = self._format_time_range(shift)

        title, intro = self._resolve_reminder_label(notification_type)

        message = (
            f"<b>🔔 {title}</b>\n\n"
            f"Halo <b>{schedule.user.fullname}</b>,\n"
            f"{intro}\n\n"
            f"<b>Shift  :</b> {shift.shift_name}\n"
            f"<b>Hari   :</b> {day_name}, {date_str}\n"
            f"<b>Waktu  :</b> {time_range}\n"
            f"<b>Jenis  :</b> {schedule.schedule_type}"
        )

        return title, message

    def _format_time_range(self, shift):
        return (
            f"{shift.start_time.strftime('%H:%M')} - "
            f"{shift.end_time.strftime('%H:%M')}"
        )

    def _resolve_time_greeting(self, now):
        if 4 <= now.hour < 11:
            return "Selamat pagi"
        if 11 <= now.hour < 15:
            return "Selamat siang"
        if 15 <= now.hour < 18:
            return "Selamat sore"
        return "Selamat malam"

    def _resolve_reminder_label(self, notification_type):
        """Ambil (title, intro) dari BEFORE_SHIFT_REMINDER_CONFIG."""
        for _, ntype, title, intro in BEFORE_SHIFT_REMINDER_CONFIG:
            if ntype == notification_type:
                return title, intro
        logger.warning(f"Unknown notification_type: {notification_type}")
        return "Reminder Jadwal", "Anda memiliki jadwal kerja."

notifier_thread   = None
notifier_instance = None
notifier_lock     = threading.Lock()


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
            daemon=True,
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
