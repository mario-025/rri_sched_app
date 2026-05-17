from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from app.models.admin import Admin
from app.models.user import User
from app.config.database import db

def login_required(f):
    """Decorator untuk check login (admin atau user)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session and 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'warning')
            return redirect(url_for('auth.login_form'))
        return f(*args, **kwargs)
    return decorated_function

def admin_only(f):
    """Decorator untuk route yang hanya bisa diakses admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Anda tidak memiliki akses', 'danger')
            return redirect(url_for('home.home'))
        return f(*args, **kwargs)
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
    # Jika sudah login, redirect ke dashboard
    if 'admin_id' in session or 'user_id' in session:
        return redirect(url_for('home.home'))
    
    return render_template('auth/login.html')

def login():
    """Handle login untuk admin atau user"""
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        login_type = request.form.get('login_type', 'admin')  # admin atau user
        
        # Validate input
        if not username or not password:
            flash('Username dan password harus diisi', 'danger')
            return redirect(url_for('auth.login_form'))
        
        if login_type == 'admin':
            # LOGIN AS ADMIN
            admin = Admin.query.filter_by(username=username).first()
            
            if not admin:
                flash('Admin username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Check if account is active
            if not admin.is_active:
                flash('Akun admin ini tidak aktif. Hubungi administrator', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Verify password
            if not check_password_hash(admin.password, password):
                flash('Admin username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Create session for admin
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_fullname'] = admin.fullname
            session['admin_role'] = admin.role
            session['login_type'] = 'admin'
            
            flash(f'Selamat datang, Admin {admin.fullname}!', 'success')
            return redirect(url_for('home.home'))
        
        else:
            # LOGIN AS USER
            user = User.query.filter_by(username=username).first()
            
            if not user:
                flash('User username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Verify password
            if not check_password_hash(user.password, password):
                flash('User username atau password salah', 'danger')
                return redirect(url_for('auth.login_form'))
            
            # Create session for user
            session['user_id'] = user.id
            session['user_username'] = user.username
            session['user_fullname'] = user.fullname
            session['login_type'] = 'user'
            
            flash(f'Selamat datang, {user.fullname}!', 'success')
            return redirect(url_for('home.home'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('auth.login_form'))

def logout():
    """Handle logout (admin atau user)"""
    login_type = session.get('login_type', 'unknown')
    session.clear()
    flash('Anda berhasil logout', 'info')
    return redirect(url_for('auth.login_form'))}
