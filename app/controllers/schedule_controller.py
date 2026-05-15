import datetime

from flask import flash, redirect, render_template, request, session
from app.models.schedule import Schedule
from app.models.user import User
from app.models.shift import Shift
from app.config.database import db
from sqlalchemy import func

from app.services.scheduler import (
    generate_schedule
)


# tampil halaman form
def schedule_form():
    return render_template(
        "schedules/form.html",
        now=datetime.datetime.now()
    )

# generate preview
def generate_schedule_preview():
    year = int(request.form["year"])
    month = int(request.form["month"])

    days_off = request.form.getlist(
        "days_off"
    )

    days_off = [
        int(day)
        for day in days_off
    ]

    schedules = generate_schedule(
        year=year,
        month=month,
        days_off=days_off
    )

    # simpan ke session
    session["preview_schedule"] = schedules

    return render_template(
        "schedules/preview.html",
        schedules=schedules
    )

def save_schedule():
    schedules = session.get(
        "preview_schedule"
    )

    if not schedules:
        flash(
            "Preview schedule tidak ditemukan",
            "danger"
        )
        return redirect("/schedules")

    # Dictionary untuk track score updates per user
    user_score_updates = {}

    for item in schedules:
        new_schedule = Schedule(
            user_id=item["user_id"],
            shift_id=item["shift_id"],
            work_date= datetime.date.fromisoformat(item["work_date"])
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

    flash(
        "Schedule berhasil disimpan",
        "success"
    )

    return redirect("/schedules")


# List seluruh schedule
def list_schedules():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    schedules = Schedule.query.options(
        db.joinedload(Schedule.user),
        db.joinedload(Schedule.shift)
    ).order_by(
        Schedule.work_date.desc()
    ).paginate(
        page=page, 
        per_page=per_page
    )
    
    return render_template(
        "schedules/index.html",
        schedules=schedules.items,
        total=schedules.total,
        pages=schedules.pages,
        current_page=page,
        max=max,
        min=min
    )


# Detail schedule per tanggal
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