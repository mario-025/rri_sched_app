import datetime
from flask import render_template
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.config.database import db


def home():
    """
    Halaman home dengan info jadwal hari ini
    """
    today = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.time()
    
    # Get all schedules untuk hari ini
    today_schedules = Schedule.query.options(
        db.joinedload(Schedule.user),
        db.joinedload(Schedule.shift)
    ).filter(
        Schedule.work_date == today
    ).all()
    
    # Sort by shift_index
    today_schedules = sorted(
        today_schedules, 
        key=lambda x: x.shift.shift_index if x.shift else 999
    )
    
    # Find current shift (yang sedang berjalan)
    current_shift = None
    for schedule in today_schedules:
        if schedule.shift and schedule.shift.start_time <= current_time <= schedule.shift.end_time:
            current_shift = schedule
            break
    
    # Find upcoming shifts (yang akan datang)
    upcoming_shifts = []
    for schedule in today_schedules:
        if schedule.shift and schedule.shift.start_time > current_time:
            upcoming_shifts.append(schedule)
    
    # Limit upcoming shifts to 2
    upcoming_shifts = upcoming_shifts[:2]
    
    return render_template(
        "home.html",
        current_time=current_time,
        today=today,
        current_shift=current_shift,
        upcoming_shifts=upcoming_shifts
    )
