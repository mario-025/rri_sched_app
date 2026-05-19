import datetime
import calendar

from flask import flash, redirect, render_template, request, session, url_for
from app.models.schedule import Schedule
from app.models.user import User
from app.models.shift import Shift
from app.models.shift_pattern import ShiftPattern
from app.config.database import db
from sqlalchemy import func
from app.controllers.auth_controller import login_required

from app.services.scheduler import (
    generate_schedule
)


# Helper function untuk generate calendar data
def get_calendar_data(year, month, schedule_type=None):
    """
    Generate calendar data dengan schedule count per tanggal
    """
    cal = calendar.monthcalendar(year, month)
    
    # Get semua schedule untuk bulan ini
    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(
        year, 
        month, 
        calendar.monthrange(year, month)[1]
    )
    
    schedules_by_date = {}
    query = Schedule.query.filter(
        Schedule.work_date >= first_day,
        Schedule.work_date <= last_day
    )
    
    # Filter by schedule_type jika diberikan
    if schedule_type:
        query = query.filter(Schedule.schedule_type == schedule_type)
    
    schedules = query.options(
        db.joinedload(Schedule.user),
        db.joinedload(Schedule.shift)
    ).all()
    
    # Group schedules by date
    for sched in schedules:
        date_key = sched.work_date.isoformat()
        if date_key not in schedules_by_date:
            schedules_by_date[date_key] = []
        schedules_by_date[date_key].append(sched)
    
    return cal, schedules_by_date


# tampil halaman form
@login_required
def schedule_form():
    patterns = ShiftPattern.query.all()
    
    return render_template(
        "schedules/form.html",
        now=datetime.datetime.now(),
        patterns=patterns
    )

# generate preview dengan tampilan kalender
def generate_schedule_preview():
    year = int(request.form["year"])
    month = int(request.form["month"])
    schedule_type = request.form.get("schedule_type", "broadcast").strip()

    days_off = request.form.getlist(
        "days_off"
    )

    days_off = [
        int(day)
        for day in days_off
    ]
    
    # Get semua pola yang dipilih user (menggunakan pola[])
    patterns_to_use = []
    pola_list = request.form.getlist("pola[]")
    
    # Filter pola yang tidak kosong dan convert ke int
    for pola_str in pola_list:
        if pola_str:
            try:
                pola_id = int(pola_str)
                patterns_to_use.append(pola_id)
            except (ValueError, TypeError):
                pass
    
    # Validasi minimal 1 pola dipilih
    if not patterns_to_use:
        flash("Minimal 1 pola shift harus dipilih", "danger")
        return redirect(url_for('schedule.schedule_form'))

    result = generate_schedule(
        year=year,
        month=month,
        days_off=days_off,
        patterns_to_use=patterns_to_use
    )
    
    # Handle error dari generate_schedule
    if result.get("error"):
        flash(result["error"], "danger")
        return redirect(url_for('schedule.schedule_form'))
    
    schedules = result.get("schedules", [])
    
    if not schedules:
        flash("Tidak ada jadwal yang berhasil dibuat. Cek konfigurasi pola shift dan jumlah pegawai.", "warning")
        return redirect(url_for('schedule.schedule_form'))

    # simpan ke session
    session["preview_schedule"] = schedules
    session["preview_schedule_type"] = schedule_type

    # Convert schedules to calendar format
    cal = calendar.monthcalendar(year, month)
    schedules_by_date = {}
    
    for sched in schedules:
        date_key = sched["work_date"]
        if date_key not in schedules_by_date:
            schedules_by_date[date_key] = []
        schedules_by_date[date_key].append(sched)
    
    month_name = calendar.month_name[month]

    return render_template(
        "schedules/preview_calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        calendar_data=cal,
        schedules_by_date=schedules_by_date,
        total_schedules=len(schedules),
        schedule_type=schedule_type
    )

@login_required
def save_schedule():
    schedules = session.get(
        "preview_schedule"
    )
    schedule_type = session.get(
        "preview_schedule_type",
        "broadcast"
    )

    if not schedules:
        flash(
            "Preview schedule tidak ditemukan",
            "danger"
        )
        return redirect(url_for('schedule.list_schedules'))

    try:
        # Dictionary untuk track score updates per user
        user_score_updates = {}

        for item in schedules:
            new_schedule = Schedule(
                user_id=item["user_id"],
                shift_id=item["shift_id"],
                work_date=datetime.date.fromisoformat(item["work_date"]),
                schedule_type=schedule_type
            )

            db.session.add(new_schedule)
            
            # Track score increment untuk user ini
            if item["user_id"] not in user_score_updates:
                user_score_updates[item["user_id"]] = 0
            user_score_updates[item["user_id"]] += item["shift_score"]

        # Flush terlebih dahulu untuk assign ID
        db.session.flush()

        # Update score untuk setiap user
        for user_id, score_increment in user_score_updates.items():
            user = User.query.get(user_id)
            if user:
                user.score += score_increment

        db.session.commit()

        # hapus preview session
        session.pop(
            "preview_schedule",
            None
        )
        session.pop(
            "preview_schedule_type",
            None
        )

        flash(
            f"Schedule '{schedule_type}' berhasil disimpan",
            "success"
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error menyimpan schedule: {str(e)}", "danger")
        return redirect(url_for('schedule.list_schedules'))

    return redirect(url_for('schedule.list_schedules'))


# List seluruh schedule dalam bentuk kalender
@login_required
def list_schedules():
    year = request.args.get('year', datetime.datetime.now().year, type=int)
    month = request.args.get('month', datetime.datetime.now().month, type=int)
    schedule_type = request.args.get('schedule_type', None)
    
    # Validate year and month
    if month < 1 or month > 12:
        month = datetime.datetime.now().month
    if year < 1900 or year > 2100:
        year = datetime.datetime.now().year
    
    # Get all available schedule types untuk dropdown filter
    all_schedule_types = db.session.query(Schedule.schedule_type).distinct().all()
    available_types = sorted([t[0] for t in all_schedule_types if t[0]])
    
    cal, schedules_by_date = get_calendar_data(year, month, schedule_type)
    
    # Get month name
    month_name = calendar.month_name[month]
    
    # Get previous and next month
    if month == 1:
        prev_month = (12, year - 1)
        next_month = (2, year)
    elif month == 12:
        prev_month = (11, year)
        next_month = (1, year + 1)
    else:
        prev_month = (month - 1, year)
        next_month = (month + 1, year)
    
    return render_template(
        "schedules/calendar.html",
        year=year,
        month=month,
        month_name=month_name,
        calendar_data=cal,
        schedules_by_date=schedules_by_date,
        prev_month=prev_month,
        next_month=next_month,
        available_types=available_types,
        selected_type=schedule_type
    )


# Detail schedule per tanggal
@login_required
def schedule_detail(work_date):
    try:
        date_obj = datetime.date.fromisoformat(work_date)
    except ValueError:
        flash(
            "Format tanggal tidak valid",
            "danger"
        )
        return redirect("/schedules")
    
    schedules = Schedule.query.join(
        Schedule.shift
    ).options(
        db.joinedload(Schedule.user),
        db.joinedload(Schedule.shift)
    ).filter(
        Schedule.work_date == date_obj
    ).order_by(
        Shift.shift_index
    ).all()
    
    if not schedules:
        flash(
            "Tidak ada jadwal untuk tanggal tersebut",
            "warning"
        )
        return redirect("/schedules")
    
    return render_template(
        "schedules/detail.html",
        work_date=work_date,
        schedules=schedules
    )


# Form edit schedule
@login_required
def edit_schedule_form(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    users = User.query.all()
    shifts = Shift.query.order_by(Shift.shift_index).all()
    
    return render_template(
        "schedules/edit.html",
        schedule=schedule,
        users=users,
        shifts=shifts
    )


# Update schedule
@login_required
def update_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    
    user_id = request.form.get("user_id", type=int)
    shift_id = request.form.get("shift_id", type=int)
    
    user = User.query.get(user_id)
    shift = Shift.query.get(shift_id)
    
    if not user:
        flash(
            "User tidak ditemukan",
            "danger"
        )
        return redirect(f"/schedules/edit/{schedule_id}")
    
    if not shift:
        flash(
            "Shift tidak ditemukan",
            "danger"
        )
        return redirect(f"/schedules/edit/{schedule_id}")
    
    # Handle score adjustment jika user atau shift berubah
    old_user_id = schedule.user_id
    old_shift_id = schedule.shift_id
    old_shift = Shift.query.get(old_shift_id)
    old_user = User.query.get(old_user_id)
    
    # Kurangi score user lama jika user berubah
    if old_user_id != user_id and old_shift:
        old_user.score -= old_shift.score
    
    # Update schedule
    schedule.user_id = user_id
    schedule.shift_id = shift_id
    
    # Tambahkan score user baru
    if old_user_id != user_id:
        # User berbeda, tambah score user baru dengan shift lama
        user.score += old_shift.score
    elif old_shift_id != shift_id:
        # User sama tapi shift berbeda
        user.score -= old_shift.score
        user.score += shift.score
    
    db.session.commit()
    
    flash(
        "Schedule berhasil diupdate",
        "success"
    )
    
    return redirect(
        f"/schedules/detail/{schedule.work_date.isoformat()}"
    )


# Delete schedule
@login_required
def delete_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    work_date = schedule.work_date.isoformat()
    
    # Kurangi score user
    user = schedule.user
    shift = schedule.shift
    user.score -= shift.score
    
    db.session.delete(schedule)
    db.session.commit()
    
    flash(
        "Schedule berhasil dihapus",
        "success"
    )
    
    return redirect(
        f"/schedules/detail/{work_date}"
    )


# Delete all schedules dan reverse semua score user
@login_required
def delete_all_schedules():
    """Delete all schedules dan reverse semua user scores"""
    try:
        # Query semua schedules
        all_schedules = Schedule.query.all()
        
        if not all_schedules:
            flash("Tidak ada jadwal yang perlu dihapus", "info")
            return redirect(url_for('schedule.list_schedules'))
        
        # Hitung berapa jadwal yang akan dihapus
        total_schedules = len(all_schedules)
        
        # Reverse scores untuk setiap schedule
        for schedule in all_schedules:
            if schedule.shift and schedule.user:
                schedule.user.score -= schedule.shift.score
        
        # Delete semua schedules
        for schedule in all_schedules:
            db.session.delete(schedule)
        
        db.session.commit()
        
        flash(
            f"Semua {total_schedules} jadwal berhasil dihapus dan score user dikembalikan",
            "success"
        )
        return redirect(url_for('schedule.list_schedules'))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error saat menghapus jadwal: {str(e)}", "danger")
        return redirect(url_for('schedule.list_schedules'))