import datetime
from flask import render_template, redirect, url_for, session
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.models.user import User
from app.config.database import db
from app.controllers.auth_controller import login_required


@login_required
def home():
    """Home page - berbeda untuk admin vs user"""
    
    login_type = session.get('login_type', 'admin')
    
    if login_type == 'user':
        return user_home()
    else:
        return admin_home()


def user_home():
    """Home page untuk user - tampilkan jadwal user sendiri yang sedang berlangsung dan upcoming"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return redirect(url_for('auth.login_form'))
        
        today = datetime.date.today()
        now = datetime.datetime.now()
        current_time = now.time()
        
        # Get user's today schedule
        today_schedule = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id,
            Schedule.work_date == today
        ).first()
        
        current_shift = None
        current_shift_status = None  # 'ongoing', 'upcoming', atau None
        
        # Check apakah user punya jadwal hari ini
        if today_schedule and today_schedule.shift:
            shift = today_schedule.shift
            # Check apakah shift sedang berlangsung
            if shift.start_time <= current_time <= shift.end_time:
                current_shift = today_schedule
                current_shift_status = 'ongoing'
            elif shift.end_time < current_time:
                # Jadwal hari ini sudah selesai
                current_shift = None
            else:
                # Jadwal hari ini belum dimulai (upcoming today)
                current_shift = today_schedule
                current_shift_status = 'upcoming_today'
        
        # Cari upcoming schedules (dari besok atau beberapa hari ke depan)
        upcoming_schedules = []
        
        if current_shift_status != 'ongoing':
            # Jika tidak sedang berlangsung, tampilkan jadwal berikutnya
            if current_shift_status == 'upcoming_today':
                # Jika ada jadwal today yang belum mulai, jangan tampilkan jadwal besok
                start_date = today
            else:
                # Jika jadwal hari ini sudah lewat atau tidak ada, mulai dari besok
                start_date = today + datetime.timedelta(days=1)
            
            end_date = today + datetime.timedelta(days=7)  # Tampilkan 7 hari ke depan
            
            upcoming_schedules = Schedule.query.options(
                db.joinedload(Schedule.shift)
            ).filter(
                Schedule.user_id == user_id,
                Schedule.work_date >= start_date,
                Schedule.work_date <= end_date
            ).order_by(
                Schedule.work_date.asc()
            ).all()
        
        return render_template(
            'user/home.html',
            user=user,
            current_shift=current_shift,
            current_shift_status=current_shift_status,
            upcoming_schedules=upcoming_schedules,
            today=today,
            current_time=current_time
        )
    
    except Exception as e:
        return render_template('errors/500.html'), 500


def admin_home():
    """Home page untuk admin - tampilkan semua jadwal hari ini"""
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
        "admin/home.html",
        current_time=current_time,
        today=today,
        current_shifts=current_shifts,
        current_shift=current_shift_obj,  # Keep for progress bar
        previous_shifts=previous_shifts,
        upcoming_shifts=upcoming_shifts
    )
