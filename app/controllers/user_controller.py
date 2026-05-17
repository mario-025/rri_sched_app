from flask import redirect, render_template, request, flash, url_for, jsonify
from datetime import datetime
from calendar import monthcalendar, month_name
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


@login_required
@admin_only
def get_all_users():
    """Get all users with upcoming schedules"""
    users = User.query.order_by(User.fullname).all()
    
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
    
    return render_template('admin/users/index.html', users=users, user_schedules=user_schedules)

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
        month_name=month_name[now.month],
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
