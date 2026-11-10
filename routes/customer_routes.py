from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from models import db, User, Account, Transaction, Notification
from utils.decorators import login_required, customer_required
from utils.helpers import generate_account_number, generate_reference_id, add_notification
from utils.pdf_generator import generate_statement_pdf, generate_receipt_pdf

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

def get_current_user():
    return User.query.get(session.get('user_id'))

@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    accounts = Account.query.filter_by(user_id=user.id).all()
    primary_account = accounts[0] if accounts else None

    # Get recent transactions across user's accounts
    account_ids = [acc.id for acc in accounts]
    recent_transactions = Transaction.query.filter(
        Transaction.account_id.in_(account_ids)
    ).order_by(Transaction.timestamp.desc()).limit(8).all() if account_ids else []

    # Calculate statistics
    total_balance = sum([Decimal(str(acc.balance)) for acc in accounts], Decimal('0.00'))
    
    total_deposits = Decimal('0.00')
    total_withdrawals = Decimal('0.00')
    if account_ids:
        dep_val = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_type.in_(['DEPOSIT', 'TRANSFER_RECEIVED']),
            Transaction.status == 'COMPLETED'
        ).scalar()
        if dep_val:
            total_deposits = Decimal(str(dep_val))

        with_val = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_type.in_(['WITHDRAWAL', 'TRANSFER_SENT']),
            Transaction.status == 'COMPLETED'
        ).scalar()
        if with_val:
            total_withdrawals = Decimal(str(with_val))

    # Calculate last 6 months transaction volume for Chart.js
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

        m_dep = Decimal('0.00')
        m_with = Decimal('0.00')
        if account_ids:
            d_val = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type.in_(['DEPOSIT', 'TRANSFER_RECEIVED']),
                Transaction.timestamp >= start_of_month,
                Transaction.timestamp < end_of_month,
                Transaction.status == 'COMPLETED'
            ).scalar()
            if d_val:
                m_dep = Decimal(str(d_val))

            w_val = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type.in_(['WITHDRAWAL', 'TRANSFER_SENT']),
                Transaction.timestamp >= start_of_month,
                Transaction.timestamp < end_of_month,
                Transaction.status == 'COMPLETED'
            ).scalar()
            if w_val:
                m_with = Decimal(str(w_val))

        monthly_deposits.append(float(m_dep))
        monthly_withdrawals.append(float(m_with))

    unread_notifs_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    return render_template(
        'customer/dashboard.html',
        user=user,
        accounts=accounts,
        primary_account=primary_account,
        recent_transactions=recent_transactions,
        total_balance=total_balance,
        total_deposits=total_deposits,
        total_withdrawals=total_withdrawals,
        chart_labels=monthly_labels,
        chart_deposits=monthly_deposits,
        chart_withdrawals=monthly_withdrawals,
        unread_notifs_count=unread_notifs_count
    )


@customer_bp.route('/accounts', methods=['GET', 'POST'])
@login_required
@customer_required
def accounts():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id).order_by(Account.created_at.desc()).all()

    if request.method == 'POST':
        account_type = request.form.get('account_type', 'Savings')
        initial_deposit_raw = request.form.get('initial_deposit', '50.00').strip()

        try:
            initial_deposit = Decimal(initial_deposit_raw)
            if initial_deposit < Decimal('25.00'):
                flash('Minimum initial deposit for opening an account is $25.00.', 'danger')
                return render_template('customer/accounts.html', accounts=user_accounts)
            if initial_deposit > Decimal('500000.00'):
                flash('Initial deposit exceeds maximum threshold ($500,000.00).', 'danger')
                return render_template('customer/accounts.html', accounts=user_accounts)
        except Exception:
            flash('Invalid initial deposit amount specified.', 'danger')
            return render_template('customer/accounts.html', accounts=user_accounts)

        if account_type not in ['Savings', 'Current']:
            account_type = 'Savings'

        try:
            new_acc_num = generate_account_number()
            new_acc = Account(
                user_id=user.id,
                account_number=new_acc_num,
                account_type=account_type,
                balance=initial_deposit,
                status='Active'
            )
            db.session.add(new_acc)
            db.session.flush()

            ref_id = generate_reference_id("DEP")
            init_txn = Transaction(
                reference_id=ref_id,
                account_id=new_acc.id,
                transaction_type='DEPOSIT',
                amount=initial_deposit,
                balance_after=initial_deposit,
                description=f'Initial opening deposit for {account_type} account',
                status='COMPLETED'
            )
            db.session.add(init_txn)

            add_notification(
                user.id,
                f'New {account_type} Account Opened',
                f'Your new {account_type} Account #{new_acc_num} has been successfully activated with an initial deposit of ${initial_deposit:,.2f}.',
                'success'
            )

            db.session.commit()
            flash(f'New {account_type} account ({new_acc_num}) created successfully!', 'success')
            return redirect(url_for('customer.accounts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to open account: {str(e)}', 'danger')

    return render_template('customer/accounts.html', accounts=user_accounts)


@customer_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
@customer_required
def deposit():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id, status='Active').all()

    if not user_accounts:
        flash('You have no active accounts available for deposit. Please contact support.', 'warning')
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount_raw = request.form.get('amount', '').strip()
        description = request.form.get('description', 'Self Account Deposit').strip()

        account = Account.query.filter_by(id=account_id, user_id=user.id).first()
        if not account or account.status != 'Active':
            flash('Invalid or inactive account selected.', 'danger')
            return render_template('customer/deposit.html', accounts=user_accounts)

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                flash('Deposit amount must be greater than $0.00.', 'danger')
                return render_template('customer/deposit.html', accounts=user_accounts)
            if amount > Decimal('250000.00'):
                flash('Single deposit amount cannot exceed $250,000.00.', 'danger')
                return render_template('customer/deposit.html', accounts=user_accounts)
        except Exception:
            flash('Please enter a valid numeric amount.', 'danger')
            return render_template('customer/deposit.html', accounts=user_accounts)

        try:
            current_bal = Decimal(str(account.balance))
            account.balance = current_bal + amount
            ref_id = generate_reference_id("DEP")
            
            txn = Transaction(
                reference_id=ref_id,
                account_id=account.id,
                transaction_type='DEPOSIT',
                amount=amount,
                balance_after=account.balance,
                description=description or 'Account Cash Deposit',
                status='COMPLETED'
            )
            db.session.add(txn)

            add_notification(
                user.id,
                'Funds Deposited Successfully',
                f'${amount:,.2f} has been deposited to account #{account.account_number}. Reference: {ref_id}',
                'success'
            )

            db.session.commit()
            flash(f'Successfully deposited ${amount:,.2f} into account {account.account_number}.', 'success')
            return redirect(url_for('customer.receipt', txn_id=txn.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Transaction failed: {str(e)}', 'danger')

    return render_template('customer/deposit.html', accounts=user_accounts)


@customer_bp.route('/withdraw', methods=['GET', 'POST'])
@login_required
@customer_required
def withdraw():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id, status='Active').all()

    if not user_accounts:
        flash('You have no active accounts available for withdrawal.', 'warning')
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        account_id = request.form.get('account_id')
        amount_raw = request.form.get('amount', '').strip()
        description = request.form.get('description', 'ATM / Counter Withdrawal').strip()

        account = Account.query.filter_by(id=account_id, user_id=user.id).first()
        if not account or account.status != 'Active':
            flash('Invalid or inactive account selected.', 'danger')
            return render_template('customer/withdraw.html', accounts=user_accounts)

        try:
            amount = Decimal(amount_raw)
            current_bal = Decimal(str(account.balance))
            if amount <= Decimal('0.00'):
                flash('Withdrawal amount must be greater than $0.00.', 'danger')
                return render_template('customer/withdraw.html', accounts=user_accounts)
            if amount > current_bal:
                flash(f'Insufficient funds! Requested: ${amount:,.2f}, Available: ${current_bal:,.2f}.', 'danger')
                return render_template('customer/withdraw.html', accounts=user_accounts)
            if amount > Decimal('50000.00'):
                flash('Single withdrawal limit is $50,000.00 per transaction.', 'danger')
                return render_template('customer/withdraw.html', accounts=user_accounts)
        except Exception:
            flash('Please enter a valid numeric amount.', 'danger')
            return render_template('customer/withdraw.html', accounts=user_accounts)

        try:
            account.balance = current_bal - amount
            ref_id = generate_reference_id("WTH")
            
            txn = Transaction(
                reference_id=ref_id,
                account_id=account.id,
                transaction_type='WITHDRAWAL',
                amount=amount,
                balance_after=account.balance,
                description=description or 'Cash Withdrawal',
                status='COMPLETED'
            )
            db.session.add(txn)

            add_notification(
                user.id,
                'Withdrawal Successful',
                f'${amount:,.2f} withdrawn from account #{account.account_number}. Reference: {ref_id}. New balance: ${account.balance:,.2f}',
                'warning'
            )

            db.session.commit()
            flash(f'Withdrawal of ${amount:,.2f} completed successfully.', 'success')
            return redirect(url_for('customer.receipt', txn_id=txn.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Transaction failed: {str(e)}', 'danger')

    return render_template('customer/withdraw.html', accounts=user_accounts)


@customer_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
@customer_required
def transfer():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id, status='Active').all()

    if not user_accounts:
        flash('You have no active accounts available to perform transfers.', 'warning')
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        sender_account_id = request.form.get('sender_account_id')
        receiver_account_num = request.form.get('receiver_account_number', '').strip().replace('-', '')
        amount_raw = request.form.get('amount', '').strip()
        description = request.form.get('description', 'Bank Fund Transfer').strip()

        # Validate sender account
        sender_account = Account.query.filter_by(id=sender_account_id, user_id=user.id).first()
        if not sender_account or sender_account.status != 'Active':
            flash('Invalid or inactive sending account.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        # Validate receiver account
        receiver_account = Account.query.filter_by(account_number=receiver_account_num).first()
        if not receiver_account:
            flash(f'Receiver account "{receiver_account_num}" was not found. Please verify the account number.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        if receiver_account.status != 'Active':
            flash('The destination account is currently inactive or suspended.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        if not receiver_account.user.is_active:
            flash('The beneficiary account holder profile is currently suspended.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        if receiver_account.id == sender_account.id:
            flash('Sender and receiver account cannot be the identical account.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        try:
            amount = Decimal(amount_raw)
            sender_bal = Decimal(str(sender_account.balance))
            receiver_bal = Decimal(str(receiver_account.balance))

            if amount <= Decimal('0.00'):
                flash('Transfer amount must be greater than $0.00.', 'danger')
                return render_template('customer/transfer.html', accounts=user_accounts)
            if amount > sender_bal:
                flash(f'Insufficient funds for transfer! Available: ${sender_bal:,.2f}.', 'danger')
                return render_template('customer/transfer.html', accounts=user_accounts)
            if amount > Decimal('50000.00'):
                flash('Single transfer exceeds maximum daily limit of $50,000.00.', 'danger')
                return render_template('customer/transfer.html', accounts=user_accounts)
        except Exception:
            flash('Please enter a valid numeric transfer amount.', 'danger')
            return render_template('customer/transfer.html', accounts=user_accounts)

        # Execute atomic transfer
        try:
            sender_account.balance = sender_bal - amount
            receiver_account.balance = receiver_bal + amount

            ref_id = generate_reference_id("TRF")

            # Outgoing transaction for sender
            sender_txn = Transaction(
                reference_id=ref_id,
                account_id=sender_account.id,
                transaction_type='TRANSFER_SENT',
                amount=amount,
                balance_after=sender_account.balance,
                description=f"Transfer to {receiver_account.user.full_name} ({receiver_account.account_number}) - {description}",
                sender_account_number=sender_account.account_number,
                receiver_account_number=receiver_account.account_number,
                status='COMPLETED'
            )
            db.session.add(sender_txn)

            # Incoming transaction for receiver
            receiver_txn = Transaction(
                reference_id=f"{ref_id}-R",
                account_id=receiver_account.id,
                transaction_type='TRANSFER_RECEIVED',
                amount=amount,
                balance_after=receiver_account.balance,
                description=f"Transfer from {sender_account.user.full_name} ({sender_account.account_number}) - {description}",
                sender_account_number=sender_account.account_number,
                receiver_account_number=receiver_account.account_number,
                status='COMPLETED'
            )
            db.session.add(receiver_txn)

            # Notifications
            add_notification(
                sender_account.user_id,
                'Money Transfer Sent',
                f'Transferred ${amount:,.2f} to {receiver_account.user.full_name} (Acc: #{receiver_account.account_number}). Ref: {ref_id}',
                'info'
            )

            add_notification(
                receiver_account.user_id,
                'Money Transfer Received',
                f'Received ${amount:,.2f} from {sender_account.user.full_name} (Acc: #{sender_account.account_number}). Ref: {ref_id}',
                'success'
            )

            db.session.commit()
            flash(f'Transfer of ${amount:,.2f} to {receiver_account.user.full_name} completed successfully!', 'success')
            return redirect(url_for('customer.receipt', txn_id=sender_txn.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Transfer transaction failed: {str(e)}', 'danger')

    return render_template('customer/transfer.html', accounts=user_accounts)


@customer_bp.route('/transactions')
@login_required
@customer_required
def transactions():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id).all()
    account_ids = [acc.id for acc in user_accounts]

    if not account_ids:
        return render_template('customer/transactions.html', transactions=[], accounts=user_accounts)

    account_filter = request.args.get('account_id')
    txn_type_filter = request.args.get('type')
    search_query = request.args.get('q', '').strip()
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    query = Transaction.query.filter(Transaction.account_id.in_(account_ids))

    if account_filter and account_filter.isdigit():
        query = query.filter(Transaction.account_id == int(account_filter))

    if txn_type_filter in ['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_SENT', 'TRANSFER_RECEIVED']:
        query = query.filter(Transaction.transaction_type == txn_type_filter)

    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            (Transaction.reference_id.ilike(search_pattern)) |
            (Transaction.description.ilike(search_pattern)) |
            (Transaction.sender_account_number.ilike(search_pattern)) |
            (Transaction.receiver_account_number.ilike(search_pattern))
        )

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
            query = query.filter(Transaction.timestamp >= from_date)
        except ValueError:
            pass

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Transaction.timestamp < to_date)
        except ValueError:
            pass

    all_txns = query.order_by(Transaction.timestamp.desc()).all()

    return render_template(
        'customer/transactions.html',
        transactions=all_txns,
        accounts=user_accounts,
        selected_account=account_filter,
        selected_type=txn_type_filter,
        search_query=search_query,
        from_date=from_date_str,
        to_date=to_date_str
    )


@customer_bp.route('/statement', methods=['GET'])
@login_required
@customer_required
def statement():
    user = get_current_user()
    user_accounts = Account.query.filter_by(user_id=user.id).all()

    account_id = request.args.get('account_id')
    selected_account = None
    if account_id and account_id.isdigit():
        selected_account = Account.query.filter_by(id=int(account_id), user_id=user.id).first()
    if not selected_account and user_accounts:
        selected_account = user_accounts[0]

    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    transactions = []
    if selected_account:
        q = Transaction.query.filter_by(account_id=selected_account.id)
        if from_date_str:
            try:
                fd = datetime.strptime(from_date_str, '%Y-%m-%d')
                q = q.filter(Transaction.timestamp >= fd)
            except ValueError:
                pass
        if to_date_str:
            try:
                td = datetime.strptime(to_date_str, '%Y-%m-%d') + timedelta(days=1)
                q = q.filter(Transaction.timestamp < td)
            except ValueError:
                pass
        transactions = q.order_by(Transaction.timestamp.desc()).all()

    statement_date = datetime.now(timezone.utc).strftime('%b %d, %Y')

    return render_template(
        'customer/statement.html',
        accounts=user_accounts,
        selected_account=selected_account,
        transactions=transactions,
        from_date=from_date_str,
        to_date=to_date_str,
        statement_date=statement_date
    )


@customer_bp.route('/statement/download')
@login_required
@customer_required
def download_statement():
    user = get_current_user()
    account_id = request.args.get('account_id')
    account = Account.query.filter_by(id=account_id, user_id=user.id).first_or_404()

    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    from_date = None
    to_date = None
    q = Transaction.query.filter_by(account_id=account.id)

    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
            q = q.filter(Transaction.timestamp >= from_date)
        except ValueError:
            pass
    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
            q = q.filter(Transaction.timestamp < to_date + timedelta(days=1))
        except ValueError:
            pass

    txns = q.order_by(Transaction.timestamp.asc()).all()

    pdf_buffer = generate_statement_pdf(account, txns, from_date, to_date)
    filename = f"statement_{account.account_number}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@customer_bp.route('/receipt/<int:txn_id>')
@login_required
@customer_required
def receipt(txn_id):
    user = get_current_user()
    txn = Transaction.query.get_or_404(txn_id)

    if txn.account.user_id != user.id:
        flash('Unauthorized access to transaction receipt.', 'danger')
        return redirect(url_for('customer.dashboard'))

    return render_template('customer/receipt.html', txn=txn)


@customer_bp.route('/receipt/<int:txn_id>/download')
@login_required
@customer_required
def download_receipt(txn_id):
    user = get_current_user()
    txn = Transaction.query.get_or_404(txn_id)

    if txn.account.user_id != user.id:
        flash('Unauthorized receipt access.', 'danger')
        return redirect(url_for('customer.dashboard'))

    pdf_buffer = generate_receipt_pdf(txn)
    filename = f"receipt_{txn.reference_id}.pdf"

    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def profile():
    user = get_current_user()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()

            if len(full_name) < 3:
                flash('Full name must be at least 3 characters long.', 'danger')
            else:
                user.full_name = full_name
                user.phone = phone
                user.address = address
                db.session.commit()
                flash('Profile information updated successfully!', 'success')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                user.set_password(new_password)
                db.session.commit()
                flash('Your password has been changed successfully!', 'success')

    return render_template('customer/profile.html', user=user)


@customer_bp.route('/notifications')
@login_required
@customer_required
def notifications():
    user = get_current_user()
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    return render_template('customer/notifications.html', notifications=notifs)
