from flask import redirect, render_template, request, flash, url_for
from datetime import datetime
from calendar import monthcalendar, month_name
from app.models.user import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.config.database import db

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
    
    return render_template('users/index.html', users=users, user_schedules=user_schedules)

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
        'users/detail.html',
        user=user,
        schedules=schedules,
        shifts_assigned=shifts_assigned,
        calendar=cal,
        year=now.year,
        month=now.month,
        month_name=month_name[now.month],
        schedule_map=schedule_map
    )

def create_form():
    """Show form for create new user"""
    return render_template('users/create.html')

def create_user():
    """Save new user"""
    try:
        fullname = request.form.get('fullname', '').strip()
        username = request.form.get('username', '').strip()
        
        # Validate
        if not fullname or not username:
            flash('Nama lengkap dan username harus diisi', 'danger')
            return redirect(url_for('user.create_form'))
        
        # Check duplicate username
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f'Username {username} sudah ada', 'danger')
            return redirect(url_for('user.create_form'))
        
        user = User(fullname=fullname, username=username, score=0)
        db.session.add(user)
        db.session.commit()
        
        flash(f'Pegawai {fullname} berhasil ditambahkan', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.create_form'))

def edit_form(user_id):
    """Show form for edit user"""
    user = User.query.get_or_404(user_id)
    return render_template('users/edit.html', user=user)

def update_user(user_id):
    """Update existing user"""
    try:
        user = User.query.get_or_404(user_id)
        
        fullname = request.form.get('fullname', '').strip()
        username = request.form.get('username', '').strip()
        
        # Validate
        if not fullname or not username:
            flash('Nama lengkap dan username harus diisi', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        # Check duplicate username (exclude current user)
        existing = User.query.filter(
            User.username == username,
            User.id != user_id
        ).first()
        if existing:
            flash(f'Username {username} sudah digunakan', 'danger')
            return redirect(url_for('user.edit_form', user_id=user_id))
        
        user.fullname = fullname
        user.username = username
        db.session.commit()
        
        flash(f'Pegawai {fullname} berhasil diperbarui', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.edit_form', user_id=user_id))

def delete_user(user_id):
    """Delete user"""
    try:
        user = User.query.get_or_404(user_id)
        fullname = user.fullname
        
        # Delete all schedules for this user first
        Schedule.query.filter_by(user_id=user_id).delete()
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Pegawai {fullname} berhasil dihapus', 'success')
        return redirect(url_for('user.get_all_users'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('user.get_all_users'))