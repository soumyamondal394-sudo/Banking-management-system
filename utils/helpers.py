import random
import string
from datetime import datetime, timezone
from decimal import Decimal
from models import db, Account, Transaction, Notification

def generate_account_number():
    """Generates a unique 10-digit account number starting with 10, 20, or 30."""
    while True:
        prefix = random.choice(['10', '20', '30'])
        suffix = ''.join(random.choices(string.digits, k=8))
        account_number = prefix + suffix
        if not Account.query.filter_by(account_number=account_number).first():
            return account_number

def generate_reference_id(prefix="TXN"):
    """Generates a unique transaction reference ID."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    while True:
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        ref_id = f"{prefix}-{date_str}-{random_suffix}"
        if not Transaction.query.filter_by(reference_id=ref_id).first():
            return ref_id

def format_currency(amount, currency_symbol="$"):
    """Formats a decimal amount as a currency string e.g., $1,250.00"""
    try:
        val = Decimal(str(amount))
        return f"{currency_symbol}{val:,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"

def mask_account_number(account_number):
    """Returns a masked version of account number e.g. 10••••4567"""
    acc_str = str(account_number)
    if len(acc_str) >= 6:
        return f"{acc_str[:2]}••••{acc_str[-4:]}"
    return acc_str

def add_notification(user_id, title, message, notif_type="info"):
    """Creates an in-app notification for a user."""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        return None
