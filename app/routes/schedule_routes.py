from flask import Blueprint

from app.controllers.schedule_controller import (
    schedule_form,
    generate_schedule_preview,
    save_schedule,
    list_schedules,
    schedule_detail,
    edit_schedule_form,
    update_schedule,
    delete_schedule,
    delete_all_schedules,
    delete_schedules_by_type,
    send_digest_reminders,
    schedule_report_form,
    schedule_report_preview_form,
    schedule_report,
)

schedule_bp = Blueprint(
    "schedule",
    __name__
)

# List schedules
schedule_bp.route(
    "/",
    methods=["GET"]
)(list_schedules)

# halaman form generate
schedule_bp.route(
    "/generate-form",
    methods=["GET"]
)(schedule_form)

# generate schedule
schedule_bp.route(
    "/generate",
    methods=["POST"]
)(generate_schedule_preview)

schedule_bp.route(
    "/save",
    methods=["POST"]
)(save_schedule)

# Detail schedule per tanggal
schedule_bp.route(
    "/detail/<work_date>",
    methods=["GET"]
)(schedule_detail)

# Edit schedule form
schedule_bp.route(
    "/edit/<int:schedule_id>",
    methods=["GET"]
)(edit_schedule_form)

# Update schedule
schedule_bp.route(
    "/update/<int:schedule_id>",
    methods=["POST"]
)(update_schedule)

# Delete schedule
schedule_bp.route(
    "/delete/<int:schedule_id>",
    methods=["POST"]
)(delete_schedule)

# Delete all schedules
schedule_bp.route(
    "/delete-all",
    methods=["POST"]
)(delete_all_schedules)

# Delete schedules berdasarkan jenis jadwal pada bulan dan tahun tertentu
schedule_bp.route(
    "/delete-by-type",
    methods=["POST"]
)(delete_schedules_by_type)

# Kirim digest 7 hari ke depan ke semua user Telegram aktif
schedule_bp.route(
    "/send-digest-reminders",
    methods=["POST"]
)(send_digest_reminders)

# Schedule report form
schedule_bp.route(
    "/report-form",
    methods=["GET"]
)(schedule_report_form)

# Schedule report preview from form
schedule_bp.route(
    "/report-preview",
    methods=["GET"]
)(schedule_report_preview_form)

# Schedule report
schedule_bp.route(
    "/report",
    methods=["GET"]
)(schedule_report)
