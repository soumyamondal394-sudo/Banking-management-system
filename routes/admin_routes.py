from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, Account, Transaction, Notification
from utils.decorators import admin_required
from utils.helpers import add_notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_customers = User.query.filter_by(role='customer').count()
    total_accounts = Account.query.count()
    
    # Calculate bank-wide totals
    total_balance_val = db.session.query(db.func.sum(Account.balance)).scalar() or Decimal('0.00')
    total_bank_balance = Decimal(str(total_balance_val))

    total_dep_val = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.transaction_type.in_(['DEPOSIT', 'TRANSFER_RECEIVED']),
        Transaction.status == 'COMPLETED'
    ).scalar() or Decimal('0.00')
    total_deposits = Decimal(str(total_dep_val))

    total_with_val = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.transaction_type.in_(['WITHDRAWAL', 'TRANSFER_SENT']),
        Transaction.status == 'COMPLETED'
    ).scalar() or Decimal('0.00')
    total_withdrawals = Decimal(str(total_with_val))

    # Today's activity
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    today_txns_count = Transaction.query.filter(Transaction.timestamp >= today_start).count()

    # Recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(10).all()

    # Recent customers
    recent_customers = User.query.filter_by(role='customer').order_by(User.created_at.desc()).limit(5).all()

    # Account types distribution
    savings_count = Account.query.filter_by(account_type='Savings').count()
    current_count = Account.query.filter_by(account_type='Current').count()

    # Active vs Suspended accounts
    active_accounts = Account.query.filter_by(status='Active').count()
    suspended_accounts = Account.query.filter(Account.status != 'Active').count()

    # Monthly Trends (last 6 months)
    monthly_labels = []
    monthly_deposits = []
    monthly_withdrawals = []

    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        
        month_label = datetime(year, month, 1).strftime('%b %Y')
        monthly_labels.append(month_label)

        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1)
        else:
            end_of_month = datetime(year, month + 1, 1)

        d_val = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(['DEPOSIT', 'TRANSFER_RECEIVED']),
            Transaction.timestamp >= start_of_month,
            Transaction.timestamp < end_of_month,
            Transaction.status == 'COMPLETED'
        ).scalar() or '0.00'

        w_val = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(['WITHDRAWAL', 'TRANSFER_SENT']),
            Transaction.timestamp >= start_of_month,
            Transaction.timestamp < end_of_month,
            Transaction.status == 'COMPLETED'
        ).scalar() or '0.00'

        monthly_deposits.append(float(d_val))
        monthly_withdrawals.append(float(w_val))

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        total_accounts=total_accounts,
        total_bank_balance=total_bank_balance,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        today_txns_count=today_txns_count,
        recent_transactions=recent_transactions,
        recent_customers=recent_customers,
        savings_count=savings_count,
        current_count=current_count,
        active_accounts=active_accounts,
        suspended_accounts=suspended_accounts,
        chart_labels=monthly_labels,
        chart_deposits=monthly_deposits,
        chart_withdrawals=monthly_withdrawals
    )


@admin_bp.route('/customers')
@admin_required
def customers():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')

    query = User.query.filter_by(role='customer')

    if search_query:
        pattern = f"%{search_query}%"
        matching_account_user_ids = db.session.query(Account.user_id).filter(
            Account.account_number.ilike(pattern)
        ).subquery()

        query = query.filter(
            (User.full_name.ilike(pattern)) |
            (User.email.ilike(pattern)) |
            (User.username.ilike(pattern)) |
            (User.phone.ilike(pattern)) |
            (User.id.in_(matching_account_user_ids))
        )

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)

    customers_list = query.order_by(User.created_at.desc()).all()

    return render_template(
        'admin/customers.html',
        customers=customers_list,
        search_query=search_query,
        status_filter=status_filter
    )


@admin_bp.route('/customer/<int:user_id>')
@admin_required
def customer_detail(user_id):
    customer = User.query.filter_by(id=user_id, role='customer').first_or_404()
    accounts = Account.query.filter_by(user_id=customer.id).all()
    account_ids = [acc.id for acc in accounts]

    transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids)
    ).order_by(Transaction.timestamp.desc()).limit(20).all() if account_ids else []

    total_balance = sum([acc.balance for acc in accounts], Decimal('0.00'))

    return render_template(
        'admin/customer_detail.html',
        customer=customer,
        accounts=accounts,
        transactions=transactions,
        total_balance=total_balance
    )


@admin_bp.route('/customer/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_customer_status(user_id):
    customer = User.query.filter_by(id=user_id, role='customer').first_or_404()
    customer.is_active = not customer.is_active
    new_status = 'Activated' if customer.is_active else 'Deactivated'
    
    add_notification(
        customer.id,
        f'Account {new_status}',
        f'Your customer profile has been {new_status.lower()} by the bank administration.',
        'warning' if not customer.is_active else 'success'
    )
    
    db.session.commit()
    flash(f'Customer {customer.full_name} status updated to {new_status}.', 'success')
    return redirect(request.referrer or url_for('admin.customers'))


@admin_bp.route('/accounts')
@admin_required
def accounts():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    query = Account.query.join(User)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            (Account.account_number.ilike(pattern)) |
            (User.full_name.ilike(pattern)) |
            (User.email.ilike(pattern))
        )

    if status_filter:
        query = query.filter(Account.status == status_filter)

    if type_filter:
        query = query.filter(Account.account_type == type_filter)

    all_accounts = query.order_by(Account.created_at.desc()).all()

    return render_template(
        'admin/accounts.html',
        accounts=all_accounts,
        search_query=search_query,
        status_filter=status_filter,
        type_filter=type_filter
    )


@admin_bp.route('/account/<int:account_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_account_status(account_id):
    account = Account.query.get_or_404(account_id)
    new_status = request.form.get('new_status')

    if new_status in ['Active', 'Suspended', 'Inactive']:
        account.status = new_status
        add_notification(
            account.user_id,
            f'Account Status Changed: {new_status}',
            f'Status for Account #{account.account_number} has been updated to {new_status}.',
            'warning' if new_status != 'Active' else 'success'
        )
        db.session.commit()
        flash(f'Account #{account.account_number} status set to {new_status}.', 'success')
    else:
        flash('Invalid account status requested.', 'danger')

    return redirect(request.referrer or url_for('admin.accounts'))


@admin_bp.route('/transactions')
@admin_required
def transactions():
    search_query = request.args.get('q', '').strip()
    txn_type = request.args.get('type', '')
    from_date_str = request.args.get('from_date', '')
    to_date_str = request.args.get('to_date', '')

    query = Transaction.query.join(Account).join(User)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            (Transaction.reference_id.ilike(pattern)) |
            (Transaction.description.ilike(pattern)) |
            (Account.account_number.ilike(pattern)) |
            (User.full_name.ilike(pattern))
        )

    if txn_type:
        query = query.filter(Transaction.transaction_type == txn_type)

    if from_date_str:
        try:
            fd = datetime.strptime(from_date_str, '%Y-%m-%d')
            query = query.filter(Transaction.timestamp >= fd)
        except ValueError:
            pass

    if to_date_str:
        try:
            td = datetime.strptime(to_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Transaction.timestamp < td)
        except ValueError:
            pass

    txns = query.order_by(Transaction.timestamp.desc()).limit(100).all()

    return render_template(
        'admin/transactions.html',
        transactions=txns,
        search_query=search_query,
        txn_type=txn_type,
        from_date=from_date_str,
        to_date=to_date_str
    )
