from decimal import Decimal
import io
from app import create_app
from models import db, User, Account, Transaction, Notification
from utils.pdf_generator import generate_statement_pdf, generate_receipt_pdf

def test_banking_system():
    print("==================================================")
    print("APEX GLOBAL BANK — AUTOMATED TEST SUITE")
    print("==================================================")

    app = create_app()
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = False

    client = app.test_client()

    with app.app_context():
        # Test 1: Verify Seed Data & Demo Accounts
        print("\n[TEST 1] Verifying Demo Test Accounts & Password Hashes...")
        admin = User.query.filter_by(username='admin').first()
        john = User.query.filter_by(username='john_doe').first()
        jane = User.query.filter_by(username='jane_smith').first()
        robert = User.query.filter_by(username='robert_brown').first()

        assert admin is not None, "Admin user must exist"
        assert john is not None, "Customer John must exist"
        assert jane is not None, "Customer Jane must exist"
        assert robert is not None, "Customer Robert must exist"

        assert admin.check_password('admin123'), "Admin credentials (admin / admin123) must be valid"
        assert john.check_password('password123'), "Customer John credentials must be valid"
        assert jane.check_password('password123'), "Customer Jane credentials must be valid"
        assert robert.check_password('password123'), "Customer Robert credentials must be valid"
        print("✓ All 4 demo accounts (1 Admin, 3 Customers) exist and verify correctly with hashed passwords.")

        # Test 2: Customer Authentication Flow
        print("\n[TEST 2] Testing Customer Authentication & Session State...")
        res = client.post('/login', data={
            'login_identifier': 'john_doe',
            'password': 'password123'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Welcome back, Johnathan Doe" in res.data or b"Account Dashboard" in res.data
        print("✓ Customer login successful and session initialized.")

        # Test 3: Customer Dashboard Rendering
        print("\n[TEST 3] Testing Customer Dashboard Components...")
        res = client.get('/customer/dashboard')
        assert res.status_code == 200
        assert b"Primary Bank Card" in res.data
        assert b"Financial Cashflow Trends" in res.data
        assert b"Recent Transactions" in res.data
        print("✓ Customer dashboard rendered all cards, virtual card, and chart components.")

        # Test 4: Deposit Money
        print("\n[TEST 4] Testing Funds Deposit...")
        acc_john = Account.query.filter_by(user_id=john.id, account_number='1001234567').first()
        initial_balance = Decimal(str(acc_john.balance))

        deposit_amt = Decimal('500.00')
        res = client.post('/customer/deposit', data={
            'account_id': acc_john.id,
            'amount': str(deposit_amt),
            'description': 'Direct Wire Deposit Test'
        }, follow_redirects=True)
        assert res.status_code == 200

        db.session.refresh(acc_john)
        expected_balance = initial_balance + deposit_amt
        assert Decimal(str(acc_john.balance)) == expected_balance
        
        dep_txn = Transaction.query.filter_by(account_id=acc_john.id, transaction_type='DEPOSIT').order_by(Transaction.timestamp.desc()).first()
        assert dep_txn is not None
        assert Decimal(str(dep_txn.amount)) == deposit_amt
        print(f"✓ Deposit of ${deposit_amt} processed atomically. New balance: ${acc_john.balance}")

        # Test 5: Overdraft Protection
        print("\n[TEST 5] Testing Overdraft Protection (Rejecting excessive withdrawal)...")
        excessive_amt = Decimal(str(acc_john.balance)) + Decimal('10000.00')
        res = client.post('/customer/withdraw', data={
            'account_id': acc_john.id,
            'amount': str(excessive_amt),
            'description': 'Attempt Overdraft'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Insufficient funds" in res.data
        print("✓ System rejected withdrawal exceeding available balance.")

        # Test 6: Valid Withdrawal
        print("\n[TEST 6] Testing Valid Funds Withdrawal...")
        withdraw_amt = Decimal('200.00')
        pre_with_balance = Decimal(str(acc_john.balance))
        res = client.post('/customer/withdraw', data={
            'account_id': acc_john.id,
            'amount': str(withdraw_amt),
            'description': 'ATM Cash Test'
        }, follow_redirects=True)
        assert res.status_code == 200

        db.session.refresh(acc_john)
        assert Decimal(str(acc_john.balance)) == (pre_with_balance - withdraw_amt)
        print(f"✓ Valid withdrawal of ${withdraw_amt} executed. Remaining: ${acc_john.balance}")

        # Test 7: Recipient Account Verification API
        print("\n[TEST 7] Testing AJAX Recipient Account Lookup API...")
        res = client.get('/api/account/lookup?account_number=1009876543')
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data['found'] is True
        assert json_data['holder_name'] == 'Jane Smith'
        assert json_data['is_active'] is True
        print(f"✓ Account lookup API verified: {json_data['holder_name']} (#{json_data['account_number']})")

        # Test 8: Inter-Account Money Transfer
        print("\n[TEST 8] Testing Inter-Account Money Transfer...")
        acc_jane = Account.query.filter_by(user_id=jane.id, account_number='1009876543').first()
        sender_initial = Decimal(str(acc_john.balance))
        receiver_initial = Decimal(str(acc_jane.balance))

        transfer_amt = Decimal('350.00')
        res = client.post('/customer/transfer', data={
            'sender_account_id': acc_john.id,
            'receiver_account_number': acc_jane.account_number,
            'amount': str(transfer_amt),
            'description': 'Contractor Payment Test'
        }, follow_redirects=True)
        assert res.status_code == 200

        db.session.refresh(acc_john)
        db.session.refresh(acc_jane)

        assert Decimal(str(acc_john.balance)) == (sender_initial - transfer_amt), "Sender balance should be debited"
        assert Decimal(str(acc_jane.balance)) == (receiver_initial + transfer_amt), "Receiver balance should be credited"
        print(f"✓ Transfer of ${transfer_amt} completed atomically.")
        print(f"  Sender New Balance:   ${acc_john.balance}")
        print(f"  Receiver New Balance: ${acc_jane.balance}")

        # Test 9: PDF Statement Generation
        print("\n[TEST 9] Testing PDF Statement Generator...")
        txns = Transaction.query.filter_by(account_id=acc_john.id).all()
        pdf_buf = generate_statement_pdf(acc_john, txns)
        pdf_bytes = pdf_buf.getvalue()
        assert pdf_bytes.startswith(b'%PDF'), "Output must be a valid PDF document"
        print(f"✓ Bank statement PDF successfully generated ({len(pdf_bytes)} bytes).")

        # Test 10: PDF Receipt Generation
        print("\n[TEST 10] Testing PDF Receipt Generator...")
        recent_txn = Transaction.query.filter_by(account_id=acc_john.id).order_by(Transaction.timestamp.desc()).first()
        rcpt_buf = generate_receipt_pdf(recent_txn)
        rcpt_bytes = rcpt_buf.getvalue()
        assert rcpt_bytes.startswith(b'%PDF'), "Receipt output must be a valid PDF document"
        print(f"✓ Transaction receipt PDF generated ({len(rcpt_bytes)} bytes).")

        # Test 11: Admin Login and Dashboard
        print("\n[TEST 11] Testing Administrator Portal Flow...")
        client.get('/logout', follow_redirects=True)
        res = client.post('/admin/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Administrative Control Center" in res.data or b"Total Bank Reserves" in res.data
        print("✓ Administrator authentication and dashboard verified.")

        # Test 12: Admin Account Freeze & Activate
        print("\n[TEST 12] Testing Admin Account Freeze/Activate...")
        res = client.post(f'/admin/account/{acc_jane.id}/toggle-status', data={
            'new_status': 'Suspended'
        }, follow_redirects=True)
        assert res.status_code == 200
        db.session.refresh(acc_jane)
        assert acc_jane.status == 'Suspended'
        print(f"✓ Account #{acc_jane.account_number} frozen to Suspended status.")

        # Reactivate
        res = client.post(f'/admin/account/{acc_jane.id}/toggle-status', data={
            'new_status': 'Active'
        }, follow_redirects=True)
        assert res.status_code == 200
        db.session.refresh(acc_jane)
        assert acc_jane.status == 'Active'
        print(f"✓ Account #{acc_jane.account_number} reactivated to Active status.")

        # Test 13: Search & Ledger Filters
        print("\n[TEST 13] Testing Search & Ledger Filters...")
        res = client.get('/admin/transactions?q=1001234567')
        assert res.status_code == 200
        assert b"1001234567" in res.data
        print("✓ Transaction audit search filter verified.")

        # Test 14: CSRF Defense Verification
        print("\n[TEST 14] Testing CSRF Token Enforcement...")
        app.config['CSRF_ENABLED'] = True
        csrf_client = app.test_client()
        # Request without CSRF token
        blocked_res = csrf_client.post('/login', data={'login_identifier': 'admin', 'password': 'admin123'})
        assert blocked_res.status_code == 403, "Untrusted POST without CSRF token must return HTTP 403"
        print("✓ CSRF Defense verified: Malicious/untrusted POST blocked with HTTP 403.")

        print("\n==================================================")
        print("ALL 14 TEST SUITES PASSED! AUDIT VERIFICATION COMPLETE")
        print("==================================================")

if __name__ == '__main__':
    test_banking_system()
