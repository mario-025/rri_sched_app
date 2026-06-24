from flask import redirect, render_template, request, flash, url_for, jsonify
from datetime import datetime
from calendar import monthcalendar
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.user import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.config.database import db
from app.controllers.auth_controller import login_required, admin_only

def generate_random_password(length=16):
    """Generate random password with letters and numbers"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

MONTHS_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}
DAYS_ID = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}

@login_required
@admin_only
def get_all_users():
    """Get all users with upcoming schedules, support search and sort"""
    # Get search and sort parameters
    search_query = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'name_asc')  # name_asc, name_desc, score_asc, score_desc
    
    # Build query
    query = User.query
    
    # Apply search filter
    if search_query:
        query = query.filter(
            User.fullname.ilike(f'%{search_query}%') |
            User.username.ilike(f'%{search_query}%') |
            User.email.ilike(f'%{search_query}%')
        )
    
    # Apply sorting
    if sort_by == 'name_desc':
        query = query.order_by(User.fullname.desc())
    elif sort_by == 'score_asc':
        query = query.order_by(User.score.asc())
    elif sort_by == 'score_desc':
        query = query.order_by(User.score.desc())
    else:  # default: name_asc
        query = query.order_by(User.fullname.asc())
    
    users = query.all()
    total_users = User.query.count()
    
    # Prepare upcoming schedules for each user
    now = datetime.now()
    user_schedules = {}
    
    for user in users:
        # Get next 3 upcoming schedules
        upcoming = Schedule.query.filter_by(user_id=user.id).options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.work_date >= now.date()
        ).order_by(Schedule.work_date).limit(3).all()
        user_schedules[user.id] = upcoming
    
    return render_template(
        'admin/users/index.html', 
        users=users, 
        total_users=total_users,
        user_schedules=user_schedules,
        search_query=search_query,
        sort_by=sort_by
    )

@login_required
@admin_only
def user_detail(user_id):
    """Show user detail with schedule and calendar"""
    user = User.query.get_or_404(user_id)
    
    # Get user schedules with shift info
    schedules = Schedule.query.filter_by(user_id=user_id).options(
        db.joinedload(Schedule.shift)
    ).order_by(Schedule.work_date).all()
    
    # Get shift assignments (unique shifts with count)
    shifts_assigned = db.session.query(Shift).join(
        Schedule, Schedule.shift_id == Shift.id
    ).filter(
        Schedule.user_id == user_id
    ).distinct().order_by(Shift.shift_index).all()
    
    # Build calendar data for current month
    now = datetime.now()
    cal = monthcalendar(now.year, now.month)
    
    # Map schedules by date (date as key)
    schedule_map = {}
    for s in schedules:
        if s.work_date.month == now.month and s.work_date.year == now.year:
            schedule_map[s.work_date.day] = s
    
    return render_template(
        'admin/users/detail.html',
        user=user,
        schedules=schedules,
        shifts_assigned=shifts_assigned,
        calendar=cal,
        year=now.year,
        month=now.month,
        month_name=MONTHS_ID[now.month],
        schedule_map=schedule_map
    )

@login_required
@admin_only
def create_form():
    """Show form for create new user"""
    # Generate initial password
    initial_password = generate_random_password()
    return render_template('admin/users/create.html', initial_password=initial_password)

@login_required
@admin_only
def create_user():
    """Save new user"""
    try:
        fullname = request.form.get('fullname', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate required fields
        if not fullname or not username or not email or not phone_number or not password:
            flash('Semua field harus diisi', 'danger')
            return redirect(url_for('user.create_form'))
        
        # Validate email format
        if '@' not in email or '.' not in email:
            flash('Format email tidak valid', 'danger')
            return redirect(url_for('user.create_form'))
        
        # Check duplicate username
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash(f'Username "{username}" sudah ada', 'danger')
            return redirect(url_for('user.create_form'))
        
        # Check duplicate email
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash(f'Email "{email}" sudah ada', 'danger')
            return redirect(url_for('user.create_form'))
        
        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(
            fullname=fullname,
            username=username,
            email=email,
            phone_number=phone_number,
            password=hashed_password,
            score=0
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'Pegawai "{fullname}" berhasil ditambahkan', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.create_form'))

@login_required
@admin_only
def edit_form(user_id):
    """Show form for edit user"""
    user = User.query.get_or_404(user_id)
    return render_template('admin/users/edit.html', user=user)

@login_required
@admin_only
def update_user(user_id):
    """Update existing user"""
    try:
        user = User.query.get_or_404(user_id)
        
        fullname = request.form.get('fullname', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validate required fields
        if not fullname or not username or not email or not phone_number:
            flash('Semua field harus diisi', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        # Validate email format
        if '@' not in email or '.' not in email:
            flash('Format email tidak valid', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        # Check duplicate username (exclude current user)
        existing_username = User.query.filter(
            User.username == username,
            User.id != user_id
        ).first()
        if existing_username:
            flash(f'Username "{username}" sudah digunakan', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        # Check duplicate email (exclude current user)
        existing_email = User.query.filter(
            User.email == email,
            User.id != user_id
        ).first()
        if existing_email:
            flash(f'Email "{email}" sudah digunakan', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        # Update basic info
        user.fullname = fullname
        user.username = username
        user.email = email
        user.phone_number = phone_number
        
        # Update password jika ada
        if password:
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
        
        db.session.commit()
        
        flash(f'Pegawai "{fullname}" berhasil diperbarui', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.edit_form', user_id=user_id))

@login_required
@admin_only
def delete_user(user_id):
    """Delete user"""
    try:
        user = User.query.get_or_404(user_id)
        fullname = user.fullname
        
        # Delete all schedules for this user first
        Schedule.query.filter_by(user_id=user_id).delete()
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Pegawai "{fullname}" berhasil dihapus', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.get_all_users'))


# API endpoint untuk generate random password
@login_required
@admin_only
def api_generate_password():
    """Generate random password via API"""
    password = generate_random_password()
    return jsonify({'password': password})

@login_required
@admin_only
def api_search_users():
    """API endpoint untuk live search users"""
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'name_asc')
    
    if not search_query or len(search_query) < 1:
        return jsonify([])
    
    # Build query
    query = User.query
    
    # Apply search filter
    query = query.filter(
        User.fullname.ilike(f'%{search_query}%') |
        User.username.ilike(f'%{search_query}%') |
        User.email.ilike(f'%{search_query}%')
    )
    
    # Apply sorting
    if sort_by == 'name_desc':
        query = query.order_by(User.fullname.desc())
    elif sort_by == 'score_asc':
        query = query.order_by(User.score.asc())
    elif sort_by == 'score_desc':
        query = query.order_by(User.score.desc())
    else:  # default: name_asc
        query = query.order_by(User.fullname.asc())
    
    users = query.all()
    
    # Prepare upcoming schedules for each user
    now = datetime.now()
    result = []
    
    for user in users:
        # Get next 3 upcoming schedules
        upcoming = Schedule.query.filter_by(user_id=user.id).options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.work_date >= now.date()
        ).order_by(Schedule.work_date).limit(3).all()
        
        schedules_data = []
        for schedule in upcoming:
            schedules_data.append({
                'shift_name': schedule.shift.shift_name,
                'work_date': schedule.work_date.strftime('%d %b %Y'),
                'start_time': schedule.shift.start_time.strftime('%H:%M'),
                'end_time': schedule.shift.end_time.strftime('%H:%M')
            })
        
        result.append({
            'id': user.id,
            'fullname': user.fullname,
            'username': user.username,
            'email': user.email,
            'phone_number': user.phone_number,
            'score': user.score,
            'schedules': schedules_data
        })
    
    return jsonify(result)


@login_required
@admin_only
def clear_telegram_data(user_id):
    """Clear telegram connection data for a user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Clear all telegram fields
        user.telegram_id = None
        user.telegram_username = None
        user.telegram_verified = False
        user.telegram_enabled = False
        user.telegram_verified_at = None
        
        db.session.commit()
        
        flash(f'Data Telegram untuk "{user.fullname}" berhasil dihapus', 'success')
        return redirect(url_for('user.user_detail', user_id=user_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.user_detail', user_id=user_id))
