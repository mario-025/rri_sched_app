"""
User Profile Controller
Handle user profile view dan schedule untuk user sendiri
"""

import datetime
import random
import string
from calendar import monthcalendar
from flask import render_template, session, redirect, url_for, flash, request, jsonify, current_app
from app.models.user import User
from app.models.schedule import Schedule
from app.models.shift import Shift
from app.config.database import db
from app.config.limiter import limiter
from app.controllers.auth_controller import user_login_required
import logging

logger = logging.getLogger(__name__)

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
        schedule_type = request.args.get('schedule_type', None)
        
        # Validate month and year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        
        # Get all schedules untuk user ini
        query = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id
        ).order_by(
            Schedule.work_date.desc()
        )
        
        # Filter by schedule_type jika diberikan
        if schedule_type:
            query = query.filter(Schedule.schedule_type == schedule_type)
        
        all_schedules = query.all()
        
        # Get available schedule types untuk user ini
        available_types = db.session.query(Schedule.schedule_type).filter(
            Schedule.user_id == user_id
        ).distinct().all()
        available_types = sorted([t[0] for t in available_types if t[0]])
        
        # Get calendar data for selected month
        cal = monthcalendar(year, month)
        
        # Get schedules for selected month with type filter
        month_query = Schedule.query.options(
            db.joinedload(Schedule.shift)
        ).filter(
            Schedule.user_id == user_id,
            db.extract('year', Schedule.work_date) == year,
            db.extract('month', Schedule.work_date) == month
        )
        
        if schedule_type:
            month_query = month_query.filter(Schedule.schedule_type == schedule_type)
        
        month_schedules = month_query.all()
        
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
            month_name=MONTHS_ID[month],
            schedule_map=schedule_map,
            prev_month=prev_month,
            prev_year=prev_year,
            next_month=next_month,
            next_year=next_year,
            current_year=now.year,
            current_month=now.month,
            available_types=available_types,
            selected_type=schedule_type
        )
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('home.home'))


# ====== TELEGRAM FUNCTIONS ======

@user_login_required
def telegram_settings():
    """Tampilkan halaman pengaturan Telegram"""
    return render_template('user/telegram_settings.html')


@user_login_required
def telegram_link():
    """Generate kode verifikasi 6 digit"""
    try:
        user_id = session.get('user_id')
        
        # Generate 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Store in app.pending_telegram_verifications
        if not hasattr(current_app, 'pending_telegram_verifications'):
            current_app.pending_telegram_verifications = {}
        
        current_app.pending_telegram_verifications[code] = {
            'user_id': user_id,
            'timestamp': datetime.datetime.now(),
            'expires_at': datetime.datetime.now() + datetime.timedelta(minutes=10)
        }
        
        logger.info(f"Generated verification code for user {user_id}: {code}")
        
        return jsonify({
            'success': True,
            'code': code
        })
    except Exception as e:
        logger.error(f"Error generating code: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_login_required
def telegram_verify():
    """Legacy manual verification endpoint"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        user_id = session.get('user_id')
        
        if not code:
            return jsonify({'success': False, 'error': 'Kode tidak boleh kosong'}), 400
        
        # Verify code exists and not expired
        if not hasattr(current_app, 'pending_telegram_verifications'):
            return jsonify({'success': False, 'error': 'Kode tidak valid atau sudah expired'}), 400
        
        if code not in current_app.pending_telegram_verifications:
            return jsonify({'success': False, 'error': 'Kode tidak valid'}), 400
        
        stored = current_app.pending_telegram_verifications[code]
        if stored['user_id'] != user_id:
            return jsonify({'success': False, 'error': 'Kode tidak sesuai'}), 400
        
        if datetime.datetime.now() > stored['expires_at']:
            del current_app.pending_telegram_verifications[code]
            return jsonify({'success': False, 'error': 'Kode sudah expired'}), 400
        
        # Code is valid, but we can't do anything without telegram_id from bot
        # This is a legacy endpoint
        return jsonify({'success': False, 'error': 'Gunakan bot untuk verifikasi'})
    
    except Exception as e:
        logger.error(f"Error in telegram_verify: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@user_login_required
@limiter.limit("60 per minute")
def telegram_status():
    """Check telegram connection status (rate limited)"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        day = DAYS_ID[user.telegram_verified_at.weekday()]
        month = MONTHS_ID[user.telegram_verified_at.month]
        if not user:
            return jsonify({'is_complete': False})
        
        # Username Telegram tidak wajib; sebagian akun hanya punya telegram_id.
        is_complete = (
            user.telegram_id and
            user.telegram_verified and
            user.telegram_enabled
        )
        
        response = {
            'is_complete': is_complete,
            'telegram_id': user.telegram_id,
            'telegram_username': user.telegram_username or '',
            'verified_at': f"{day}, {user.telegram_verified_at.day} {month} {user.telegram_verified_at.year} {user.telegram_verified_at.strftime('%H:%M:%S')}" if user.telegram_verified_at else None
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error checking telegram status: {str(e)}")
        return jsonify({'is_complete': False}), 500


def telegram_verify_from_bot():
    """Verify telegram connection from bot (PUBLIC, no login required)"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        telegram_id = str(data.get('telegram_id', '')).strip()
        username = data.get('username', '').strip()
        bot_token = data.get('bot_token', '')
        
        logger.info(f"[VERIFY] Received verification request: code={code}, telegram_id={telegram_id}, username={username}")
        
        # Validate bot token
        if bot_token != current_app.config.get('TELEGRAM_BOT_TOKEN'):
            logger.warning(f"[VERIFY] Invalid bot token in verify request")
            return jsonify({'success': False, 'error': 'Invalid bot token'}), 401
        
        if not code or not telegram_id:
            logger.warning(f"[VERIFY] Missing required fields: code={bool(code)}, telegram_id={bool(telegram_id)}")
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Verify code
        if not hasattr(current_app, 'pending_telegram_verifications'):
            logger.error(f"[VERIFY] pending_telegram_verifications dict not initialized! APP RESTART detected!")
            return jsonify({
                'success': False, 
                'error': 'Kode tidak ditemukan. Aplikasi mungkin baru di-restart. Harap dapatkan kode verifikasi baru.'
            }), 400
        
        logger.info(f"[VERIFY] Pending codes available: {list(current_app.pending_telegram_verifications.keys())}")
        
        if code not in current_app.pending_telegram_verifications:
            logger.warning(f"[VERIFY] Code not found in storage: {code}")
            return jsonify({
                'success': False, 
                'error': 'Kode tidak valid. Harap dapatkan kode verifikasi baru.'
            }), 400
        
        stored = current_app.pending_telegram_verifications[code]
        
        # Check expiry with detailed logging
        current_time = datetime.datetime.now()
        expires_at = stored['expires_at']
        time_remaining = expires_at - current_time
        
        logger.info(f"[VERIFY] Code expiry check: current={current_time}, expires_at={expires_at}, remaining={time_remaining}")
        
        if current_time > expires_at:
            del current_app.pending_telegram_verifications[code]
            logger.warning(f"[VERIFY] Code expired: {code} (expired {-time_remaining} ago)")
            return jsonify({
                'success': False, 
                'error': 'Kode sudah kadaluarsa (berlaku 10 menit). Harap dapatkan kode verifikasi baru.'
            }), 400
        
        user_id = stored['user_id']
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"[VERIFY] User not found: user_id={user_id}")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        logger.info(f"[VERIFY] User found: user_id={user_id}, username={user.username}")
        
        # Check telegram_id is not already used by another user
        existing = User.query.filter(
            User.telegram_id == telegram_id,
            User.id != user_id
        ).first()
        
        if existing:
            logger.warning(f"[VERIFY] Telegram ID already linked: {telegram_id} -> user {existing.id}")
            return jsonify({'success': False, 'error': 'Telegram ID sudah terhubung ke user lain'}), 400
        
        # Update user
        user.telegram_id = telegram_id
        user.telegram_username = username
        user.telegram_verified = True
        user.telegram_enabled = True
        user.telegram_verified_at = datetime.datetime.now()
        
        # Delete used code
        del current_app.pending_telegram_verifications[code]
        
        db.session.commit()
        logger.info(f"[VERIFY] SUCCESS: User {user.username} verified Telegram {telegram_id}")
        return jsonify({'success': True, 'message': 'Verification successful'})
    
    except Exception as e:
        logger.error(f"[VERIFY] ERROR in telegram_verify_from_bot: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False, 
            'error': f'Terjadi kesalahan sistem. Silakan hubungi administrator. Error: {str(e)}'
        }), 500


@user_login_required
def telegram_unlink():
    """Putus koneksi Telegram"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Clear telegram data
        user.telegram_id = None
        user.telegram_username = None
        user.telegram_verified = False
        user.telegram_enabled = False
        user.telegram_verified_at = None
        
        db.session.commit()
        logger.info(f"User {user_id} unlinked Telegram")
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error unlinking telegram: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
