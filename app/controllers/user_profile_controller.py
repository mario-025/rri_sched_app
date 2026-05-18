"""
User Profile Controller
Handle user profile view dan schedule untuk user sendiri
"""

import datetime
from calendar import monthcalendar, month_name
from flask import render_template, session, redirect, url_for, flash, request
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
    """Tampilkan semua jadwal milik user dalam bentuk kalender penuh dengan navigasi bulan"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            flash('User tidak ditemukan', 'danger')
            return redirect(url_for('home.home'))
        
        # Get month and year from request or use current date
        now = datetime.datetime.now()
        year = request.args.get('year', default=now.year, type=int)
        month = request.args.get('month', default=now.month, type=int)
        
        # Validate month and year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        
        # Get all schedules untuk user ini
        all_schedules = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id
        ).order_by(
            Schedule.work_date.desc()
        ).all()
        
        # Get calendar data for selected month
        cal = monthcalendar(year, month)
        
        # Get schedules for selected month
        month_schedules = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id,
            db.extract('year', Schedule.work_date) == year,
            db.extract('month', Schedule.work_date) == month
        ).all()
        
        # Map schedules by date
        schedule_map = {}
        for s in month_schedules:
            schedule_map[s.work_date.day] = s
        
        # Calculate previous and next month navigation
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        
        next_month = month + 1
        next_year = year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        return render_template(
            'user/my_schedules.html',
            user=user,
            schedules=all_schedules,
            calendar=cal,
            year=year,
            month=month,
            month_name=month_name[month],
            schedule_map=schedule_map,
            prev_month=prev_month,
            prev_year=prev_year,
            next_month=next_month,
            next_year=next_year,
            current_year=now.year,
            current_month=now.month
        )
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('home.home'))
