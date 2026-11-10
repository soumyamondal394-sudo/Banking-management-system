from datetime import datetime, timezone
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='customer')  # 'customer' or 'admin'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    accounts = db.relationship('Account', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def primary_account(self):
        return self.accounts[0] if self.accounts else None

    @property
    def total_balance(self):
        return sum([Decimal(str(acc.balance)) for acc in self.accounts], Decimal('0.00'))

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    account_type = db.Column(db.String(20), nullable=False, default='Savings')  # 'Savings' or 'Current'
    balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    status = db.Column(db.String(20), nullable=False, default='Active')  # 'Active', 'Inactive', 'Suspended'
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    transactions = db.relationship('Transaction', backref='account', lazy=True, cascade='all, delete-orphan', order_by='desc(Transaction.timestamp)')

    @property
    def is_active_account(self):
        return self.status == 'Active'

    @property
    def formatted_account_number(self):
        s = str(self.account_number)
        if len(s) == 10:
            return f"{s[:3]}-{s[3:6]}-{s[6:]}"
        return s

    @property
    def total_deposits(self):
        deposits = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.account_id == self.id,
            Transaction.transaction_type.in_(['DEPOSIT', 'TRANSFER_RECEIVED']),
            Transaction.status == 'COMPLETED'
        ).scalar()
        return Decimal(str(deposits or '0.00'))

    @property
    def total_withdrawals(self):
        withdrawals = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.account_id == self.id,
            Transaction.transaction_type.in_(['WITHDRAWAL', 'TRANSFER_SENT']),
            Transaction.status == 'COMPLETED'
        ).scalar()
        return Decimal(str(withdrawals or '0.00'))

    def __repr__(self):
        return f'<Account {self.account_number} ({self.account_type}) - Balance: {self.balance}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    reference_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'DEPOSIT', 'WITHDRAWAL', 'TRANSFER_SENT', 'TRANSFER_RECEIVED'
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    balance_after = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    sender_account_number = db.Column(db.String(20), nullable=True)
    receiver_account_number = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='COMPLETED')  # 'COMPLETED', 'PENDING', 'FAILED'
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)

    @property
    def is_credit(self):
        return self.transaction_type in ['DEPOSIT', 'TRANSFER_RECEIVED']

    @property
    def badge_color(self):
        colors = {
            'DEPOSIT': 'success',
            'WITHDRAWAL': 'warning',
            'TRANSFER_SENT': 'danger',
            'TRANSFER_RECEIVED': 'info'
        }
        return colors.get(self.transaction_type, 'secondary')

    def __repr__(self):
        return f'<Transaction {self.reference_id} - {self.transaction_type} {self.amount}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='info')  # 'info', 'success', 'warning', 'danger'
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    def __repr__(self):
        return f'<Notification {self.title} for User {self.user_id}>'
