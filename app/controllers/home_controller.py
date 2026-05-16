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
    
    # Find current shifts (semua pegawai yang sedang berjalan)
    current_shifts = []
    current_shift_obj = None
    for schedule in today_schedules:
        if schedule.shift and schedule.shift.start_time <= current_time <= schedule.shift.end_time:
            current_shifts.append(schedule)
            if not current_shift_obj:  # Store first shift object untuk progress bar
                current_shift_obj = schedule
    
    # Find previous shifts (yang sudah selesai)
    previous_shifts = []
    for schedule in today_schedules:
        if schedule.shift and schedule.shift.end_time < current_time:
            previous_shifts.append(schedule)
    
    # Group previous shifts by shift_id untuk menampilkan per shift
    previous_shifts_grouped = {}
    for schedule in previous_shifts:
        shift_id = schedule.shift.id
        if shift_id not in previous_shifts_grouped:
            previous_shifts_grouped[shift_id] = {
                'shift': schedule.shift,
                'workers': []
            }
        previous_shifts_grouped[shift_id]['workers'].append(schedule.user)
    
    # Find upcoming shifts (yang akan datang) - group by shift
    upcoming_shifts_grouped = {}
    for schedule in today_schedules:
        if schedule.shift and schedule.shift.start_time > current_time:
            shift_id = schedule.shift.id
            if shift_id not in upcoming_shifts_grouped:
                upcoming_shifts_grouped[shift_id] = {
                    'shift': schedule.shift,
                    'workers': []
                }
            upcoming_shifts_grouped[shift_id]['workers'].append(schedule.user)
    
    # Convert to list dan sort by shift_index
    upcoming_shifts = sorted(
        upcoming_shifts_grouped.values(),
        key=lambda x: x['shift'].shift_index
    )
    previous_shifts = sorted(
        previous_shifts_grouped.values(),
        key=lambda x: x['shift'].shift_index,
        reverse=True  # Show most recent first
    )
    
    return render_template(
        "home.html",
        current_time=current_time,
        today=today,
        current_shifts=current_shifts,
        current_shift=current_shift_obj,  # Keep for progress bar
        previous_shifts=previous_shifts,
        upcoming_shifts=upcoming_shifts
    )
