from functools import wraps
from flask import session, redirect, url_for, flash, request
from models import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        # Verify account active status in database
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account is inactive or has been suspended by administration.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin authentication required. Please log in.', 'warning')
            return redirect(url_for('auth.admin_login', next=request.url))

        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Administrator account is inactive or suspended.', 'danger')
            return redirect(url_for('auth.admin_login'))

        if session.get('user_role') != 'admin' or user.role != 'admin':
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('customer.dashboard'))

        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access your account.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
