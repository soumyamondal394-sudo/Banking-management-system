import os
import re
import glob
from datetime import datetime, timezone
from decimal import Decimal
from app import create_app
from models import db, User, Account, Transaction, Notification

app = create_app()

def audit_templates_and_routes():
    print("==================================================")
    print("AUDIT 1: TEMPLATE URL_FOR ENDPOINTS & HTML INTEGRITY")
    print("==================================================")
    endpoints = set(rule.endpoint for rule in app.url_map.iter_rules())
    
    html_files = glob.glob('templates/**/*.html', recursive=True)
    url_for_pattern = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")
    
    missing_endpoints = []
    for hf in html_files:
        with open(hf, 'r', encoding='utf-8') as f:
            content = f.read()
        matches = url_for_pattern.findall(content)
        for ep in matches:
            if ep == 'static':
                continue
            if ep not in endpoints:
                missing_endpoints.append((hf, ep))

    if missing_endpoints:
        print("[FAIL] Missing or invalid endpoints found:")
        for hf, ep in missing_endpoints:
            print(f"  - {hf}: url_for('{ep}')")
    else:
        print(f"[OK] All url_for calls across {len(html_files)} templates are valid.")

def audit_csrf_protection():
    print("\n==================================================")
    print("AUDIT 2: CSRF SECURITY ENFORCEMENT AUDIT")
    print("==================================================")
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = True  # Enable CSRF enforcement
    client = app.test_client()

    # Step A: POST without CSRF token should be BLOCKED with 403
    res = client.post('/login', data={'login_identifier': 'john_doe', 'password': 'password123'})
    if res.status_code == 403:
        print("[OK] CSRF Protection successfully blocked POST request lacking CSRF token (HTTP 403).")
    else:
        print(f"[FAIL] CSRF Protection did not block request without token! Status: {res.status_code}")

    # Step B: Get CSRF token by loading login page first
    res = client.get('/login')
    with client.session_transaction() as sess:
        token = sess.get('_csrf_token')

    assert token is not None, "CSRF token must be initialized in session"

    # Step C: POST with valid CSRF token should succeed
    res = client.post('/login', data={
        'csrf_token': token,
        'login_identifier': 'john_doe',
        'password': 'password123'
    }, follow_redirects=False)

    if res.status_code == 302 and '/customer/dashboard' in res.headers.get('Location', ''):
        print("[OK] CSRF Protection permitted legitimate request with valid CSRF token.")
    else:
        print(f"[FAIL] Login with valid CSRF token failed! Status: {res.status_code}")

def audit_routes_and_access_control():
    print("\n==================================================")
    print("AUDIT 3: ROLE-BASED ACCESS CONTROL & SECURITY CHECKS")
    print("==================================================")
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        # Check unauthenticated access to customer routes
        protected_customer_urls = [
            '/customer/dashboard',
            '/customer/accounts',
            '/customer/deposit',
            '/customer/withdraw',
            '/customer/transfer',
            '/customer/transactions',
            '/customer/statement',
            '/customer/profile',
            '/customer/notifications'
        ]
        
        unauth_customer_leaks = []
        for url in protected_customer_urls:
            res = client.get(url, follow_redirects=False)
            if res.status_code != 302 or '/login' not in (res.headers.get('Location') or ''):
                unauth_customer_leaks.append((url, res.status_code))

        if unauth_customer_leaks:
            print(f"[FAIL] Unauthenticated access leaks on customer routes: {unauth_customer_leaks}")
        else:
            print("[OK] All customer routes strictly redirect unauthenticated requests to /login.")

        protected_admin_urls = [
            '/admin/dashboard',
            '/admin/customers',
            '/admin/accounts',
            '/admin/transactions'
        ]

        unauth_admin_leaks = []
        for url in protected_admin_urls:
            res = client.get(url, follow_redirects=False)
            if res.status_code != 302 or '/admin/login' not in (res.headers.get('Location') or ''):
                unauth_admin_leaks.append((url, res.status_code))

        if unauth_admin_leaks:
            print(f"[FAIL] Unauthenticated access leaks on admin routes: {unauth_admin_leaks}")
        else:
            print("[OK] All admin routes strictly redirect unauthenticated requests to /admin/login.")

        # Customer attempting to access admin routes
        client.post('/login', data={'login_identifier': 'john_doe', 'password': 'password123'})
        customer_to_admin_leaks = []
        for url in protected_admin_urls:
            res = client.get(url, follow_redirects=False)
            if res.status_code != 302 or '/customer/dashboard' not in (res.headers.get('Location') or ''):
                customer_to_admin_leaks.append((url, res.status_code, res.headers.get('Location')))

        if customer_to_admin_leaks:
            print(f"[FAIL] Customer allowed into admin routes: {customer_to_admin_leaks}")
        else:
            print("[OK] Customers are forbidden from accessing admin routes and redirected to dashboard.")

        client.get('/logout')

        # Admin attempting to access customer routes
        client.post('/admin/login', data={'username': 'admin', 'password': 'admin123'})
        admin_to_customer_leaks = []
        for url in ['/customer/dashboard', '/customer/deposit', '/customer/withdraw']:
            res = client.get(url, follow_redirects=False)
            if res.status_code != 302 or '/admin/dashboard' not in (res.headers.get('Location') or ''):
                admin_to_customer_leaks.append((url, res.status_code, res.headers.get('Location')))

        if admin_to_customer_leaks:
            print(f"[FAIL] Admin was not redirected to admin dashboard from customer route: {admin_to_customer_leaks}")
        else:
            print("[OK] Admin is automatically redirected to admin dashboard when navigating to customer routes.")

        client.get('/logout')

def audit_financial_edge_cases():
    print("\n==================================================")
    print("AUDIT 4: FINANCIAL INTEGRITY & EDGE CASES")
    print("==================================================")
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = False
    client = app.test_client()

    with app.app_context():
        john = User.query.filter_by(username='john_doe').first()
        acc = Account.query.filter_by(user_id=john.id).first()

        client.post('/login', data={'login_identifier': 'john_doe', 'password': 'password123'})

        # Test A: Negative Deposit
        bal_before = Decimal(str(acc.balance))
        res = client.post('/customer/deposit', data={
            'account_id': acc.id,
            'amount': '-100.00',
            'description': 'Negative deposit test'
        }, follow_redirects=True)
        db.session.refresh(acc)
        if acc.balance != bal_before:
            print("[FAIL] Negative deposit was accepted!")
        else:
            print("[OK] Negative deposit rejected correctly.")

        # Test B: Zero Deposit
        bal_before = Decimal(str(acc.balance))
        res = client.post('/customer/deposit', data={
            'account_id': acc.id,
            'amount': '0.00',
            'description': 'Zero deposit test'
        }, follow_redirects=True)
        db.session.refresh(acc)
        if acc.balance != bal_before:
            print("[FAIL] Zero deposit was accepted!")
        else:
            print("[OK] Zero deposit rejected correctly.")

        # Test C: Negative Withdrawal
        bal_before = Decimal(str(acc.balance))
        res = client.post('/customer/withdraw', data={
            'account_id': acc.id,
            'amount': '-50.00',
            'description': 'Negative withdrawal test'
        }, follow_redirects=True)
        db.session.refresh(acc)
        if acc.balance != bal_before:
            print("[FAIL] Negative withdrawal was accepted!")
        else:
            print("[OK] Negative withdrawal rejected correctly.")

        # Test D: Non-numeric Amount
        res = client.post('/customer/deposit', data={
            'account_id': acc.id,
            'amount': 'abc_invalid',
            'description': 'Invalid amount test'
        }, follow_redirects=True)
        db.session.refresh(acc)
        if acc.balance != bal_before:
            print("[FAIL] Non-numeric amount was accepted!")
        else:
            print("[OK] Non-numeric amount rejected correctly.")

        # Test E: Transfer to Self Same Account
        res = client.post('/customer/transfer', data={
            'sender_account_id': acc.id,
            'receiver_account_number': acc.account_number,
            'amount': '50.00',
            'description': 'Self-transfer test'
        }, follow_redirects=True)
        if b"cannot be the identical account" not in res.data:
            print("[FAIL] Self same-account transfer was not blocked!")
        else:
            print("[OK] Transfer to identical account blocked correctly.")

        # Test F: Transfer to Non-Existent Account
        res = client.post('/customer/transfer', data={
            'sender_account_id': acc.id,
            'receiver_account_number': '9999999999',
            'amount': '50.00',
            'description': 'Non-existent account transfer test'
        }, follow_redirects=True)
        if b"not found" not in res.data:
            print("[FAIL] Transfer to non-existent account did not show error!")
        else:
            print("[OK] Transfer to non-existent account rejected with clear error.")

        client.get('/logout')

def audit_code_quality_and_deprecations():
    print("\n==================================================")
    print("AUDIT 5: CODE QUALITY & DEPRECATION WARNINGS")
    print("==================================================")
    py_files = [f for f in glob.glob('**/*.py', recursive=True) if not f.startswith('audit_system')]
    deprecated_calls = []
    
    for f in py_files:
        with open(f, 'r', encoding='utf-8') as pyf:
            lines = pyf.readlines()
        for idx, line in enumerate(lines, 1):
            if 'utcnow()' in line:
                deprecated_calls.append((f, idx, 'datetime.utcnow() is deprecated'))

    if deprecated_calls:
        print(f"[WARN] Found {len(deprecated_calls)} deprecated datetime.utcnow() calls:")
        for f, line_no, msg in deprecated_calls:
            print(f"  - {f}:{line_no}: {msg}")
    else:
        print("[OK] Zero deprecated datetime calls found across all application code.")

if __name__ == '__main__':
    audit_templates_and_routes()
    audit_csrf_protection()
    audit_routes_and_access_control()
    audit_financial_edge_cases()
    audit_code_quality_and_deprecations()
