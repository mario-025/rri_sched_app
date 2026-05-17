"""
User Profile Controller
Handle user profile view dan schedule untuk user sendiri
"""

import datetime
from flask import render_template, session, redirect, url_for, flash
from app.models.user import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.config.database import db
from app.controllers.auth_controller import user_login_required


@user_login_required
def user_profile():
    """Tampilkan profile user (read-only)"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            flash('User tidak ditemukan', 'danger')
            return redirect(url_for('home.home'))
        
        return render_template(
            'user/profile.html',
            user=user
        )
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('home.home'))


@user_login_required
def user_my_schedules():
    """Tampilkan semua jadwal milik user"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            flash('User tidak ditemukan', 'danger')
            return redirect(url_for('home.home'))
        
        # Get all schedules untuk user ini
        schedules = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id
        ).order_by(
            Schedule.work_date.desc()
        ).all()
        
        return render_template(
            'user/my_schedules.html',
            user=user,
            schedules=schedules
        )
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
