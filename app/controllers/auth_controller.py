from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from datetime import datetime, timedelta
from app.models.admin import Admin
from app.models.user import User
from app.config.database import db

# Session timeout for admin (in seconds)
ADMIN_SESSION_TIMEOUT = 5 * 60  # 5 minutes

def expire_admin_session_if_needed():
    """Return True jika session admin sudah expired dan sudah di-clear."""
    if 'admin_id' not in session:
        return False

    session_start = session.get('session_start_time')
    if not session_start:
        session.clear()
        return True

    try:
        start_time = datetime.fromisoformat(session_start)
    except (TypeError, ValueError):
        session.clear()
        return True

    elapsed = datetime.now() - start_time
    if elapsed > timedelta(seconds=ADMIN_SESSION_TIMEOUT):
        session.clear()
        return True

    session['session_start_time'] = datetime.now().isoformat()
    return False


def enforce_admin_session_timeout():
    """Global guard untuk memaksa logout admin setelah idle 5 menit."""
    if expire_admin_session_if_needed():
        flash('Sesi telah berakhir. Silakan login kembali.', 'warning')
        return redirect(url_for('auth.login_form'))

    return None


def check_admin_session_timeout(f):
    """Decorator untuk check admin session timeout (5 menit)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        timeout_response = enforce_admin_session_timeout()
        if timeout_response:
            return timeout_response
        
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """Decorator untuk check login (admin atau user)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session and 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('auth.login_form'))
        return check_admin_session_timeout(f)(*args, **kwargs)
    return decorated_function

def admin_only(f):
    """Decorator untuk route yang hanya bisa diakses admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Anda tidak memiliki akses', 'danger')
            return redirect(url_for('home.home'))
        return check_admin_session_timeout(f)(*args, **kwargs)
    return decorated_function

def user_login_required(f):
    """Decorator untuk check user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login sebagai user terlebih dahulu', 'warning')
            return redirect(url_for('auth.login_form'))
        return f(*args, **kwargs)
    return decorated_function

def login_form():
    """Show login form"""
    timeout_response = enforce_admin_session_timeout()
    if timeout_response:
        return timeout_response

    # Jika sudah login, redirect ke dashboard
    if 'admin_id' in session or 'user_id' in session:
        return redirect(url_for('home.home'))
    
    return render_template('auth/login.html')

def login():
    """Handle login untuk admin atau user (auto-detect)"""
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember', False)
        
        # Validate input
        if not username or not password:
            flash('Username dan password harus diisi', 'danger')
            return redirect(url_for('auth.login_form'))
        
        # Try to find in Admin table first
        admin = Admin.query.filter_by(username=username).first()
        
        if admin:
            # Check if account is active
            if not admin.is_active:
                flash('Akun admin ini tidak aktif. Hubungi administrator', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Verify password
            if not check_password_hash(admin.password, password):
                flash('Username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Create session for admin with timeout tracking
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_fullname'] = admin.fullname
            session['admin_role'] = admin.role
            session['login_type'] = 'admin'
            session['session_start_time'] = datetime.now().isoformat()  # Track session start time
            
            flash(f'Selamat datang, Admin {admin.fullname}!', 'success')
            return redirect(url_for('home.home'))
        
        # Try to find in User table
        user = User.query.filter_by(username=username).first()
        
        if user:
            # Verify password
            if not check_password_hash(user.password, password):
                flash('Username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Create session for user
            session['user_id'] = user.id
            session['user_username'] = user.username
            session['user_fullname'] = user.fullname
            session['login_type'] = 'user'
            
            flash(f'Selamat datang, {user.fullname}!', 'success')
            return redirect(url_for('home.home'))
        
        # Username not found in either table
        flash('Username atau password salah', 'danger')
        return redirect(url_for('auth.login_form'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('auth.login_form'))

def logout():
    """Handle logout (admin atau user)"""
    login_type = session.get('login_type', 'unknown')
    session.clear()
    flash('Anda berhasil logout', 'info')
    return redirect(url_for('auth.login_form'))
