import re
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Account, Transaction
from utils.helpers import generate_account_number, generate_reference_id, add_notification

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_identifier or not password:
            flash('Please enter both your username/email and password.', 'danger')
            return render_template('auth/login.html')

        # Check by username or email
        user = User.query.filter(
            (User.username == login_identifier) | (User.email == login_identifier.lower())
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact bank administration.', 'danger')
                return render_template('auth/login.html')

            # Set session
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['user_role'] = user.role
            session.permanent = remember

            flash(f'Welcome back, {user.full_name}!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.dashboard'))
        else:
            flash('Invalid username/email or password. Please try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('user_role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please provide admin credentials.', 'danger')
            return render_template('auth/admin_login.html')

        user = User.query.filter_by(username=username, role='admin').first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Admin account is suspended.', 'danger')
                return render_template('auth/admin_login.html')

            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['user_role'] = 'admin'
            session.permanent = False

            flash('Administrator authentication successful. Welcome to Control Center.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid administrative credentials or insufficient privileges.', 'danger')

    return render_template('auth/admin_login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        account_type = request.form.get('account_type', 'Savings')
        initial_deposit_raw = request.form.get('initial_deposit', '50.00').strip()

        # Validations
        errors = []
        if len(full_name) < 3:
            errors.append('Full name must be at least 3 characters long.')
        if not re.match(r'^[a-zA-Z0-9_]{3,25}$', username):
            errors.append('Username must be 3-25 alphanumeric characters or underscores.')
        if not re.match(EMAIL_REGEX, email):
            errors.append('Please provide a valid email address.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        try:
            initial_deposit = Decimal(initial_deposit_raw)
            if initial_deposit < Decimal('25.00'):
                errors.append('Minimum initial deposit is $25.00.')
            if initial_deposit > Decimal('1000000.00'):
                errors.append('Initial deposit exceeds maximum threshold ($1,000,000.00).')
        except Exception:
            errors.append('Please enter a valid numeric initial deposit amount.')

        if account_type not in ['Savings', 'Current']:
            account_type = 'Savings'

        # Uniqueness checks
        if User.query.filter_by(username=username).first():
            errors.append('Username is already registered. Please choose another.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/register.html', form_data=request.form)

        # Create user & account in atomic transaction
        try:
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                phone=phone,
                address=address,
                role='customer',
                is_active=True
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()  # to obtain new_user.id

            # Create bank account
            acc_number = generate_account_number()
            new_account = Account(
                user_id=new_user.id,
                account_number=acc_number,
                account_type=account_type,
                balance=initial_deposit,
                status='Active'
            )
            db.session.add(new_account)
            db.session.flush()

            # Record initial deposit transaction
            ref_id = generate_reference_id("DEP")
            init_txn = Transaction(
                reference_id=ref_id,
                account_id=new_account.id,
                transaction_type='DEPOSIT',
                amount=initial_deposit,
                balance_after=initial_deposit,
                description='Account opening initial deposit',
                status='COMPLETED'
            )
            db.session.add(init_txn)

            # Add welcome notification
            welcome_notif = Notification(
                user_id=new_user.id,
                title='Welcome to Apex Global Bank!',
                message=f'Your new {account_type} account ({acc_number}) has been created with an opening balance of ${initial_deposit:,.2f}.',
                type='success'
            )
            db.session.add(welcome_notif)

            db.session.commit()

            # Auto-login newly registered user
            session.clear()
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            session['full_name'] = new_user.full_name
            session['user_role'] = 'customer'

            flash(f'Account created successfully! Your new account number is {acc_number}.', 'success')
            return redirect(url_for('customer.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during account creation: {str(e)}', 'danger')
            return render_template('auth/register.html', form_data=request.form)

    return render_template('auth/register.html', form_data={})


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out. Thank you for banking with us.', 'info')
    return redirect(url_for('auth.login'))

