from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app import create_app
from models import db, User, Account, Transaction, Notification

app = create_app()

def seed_database():
    with app.app_context():
        print("Clearing existing records...")
        db.drop_all()
        db.create_all()

        print("Creating Administrator...")
        admin = User(
            username='admin',
            email='admin@apexbank.com',
            full_name='System Administrator',
            phone='+1 (800) 555-0199',
            address='Apex Global HQ, 100 Wall Street, New York, NY',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

        print("Creating Customer Accounts...")
        # Customer 1
        user1 = User(
            username='john_doe',
            email='john@example.com',
            full_name='Johnathan Doe',
            phone='+1 (555) 234-5678',
            address='742 Evergreen Terrace, Springfield, OR',
            role='customer',
            is_active=True
        )
        user1.set_password('password123')
        db.session.add(user1)

        # Customer 2
        user2 = User(
            username='jane_smith',
            email='jane@example.com',
            full_name='Jane Smith',
            phone='+1 (555) 876-5432',
            address='1204 Elm Boulevard, Metropolis, NY',
            role='customer',
            is_active=True
        )
        user2.set_password('password123')
        db.session.add(user2)

        # Customer 3
        user3 = User(
            username='robert_brown',
            email='robert@example.com',
            full_name='Robert Brown',
            phone='+1 (555) 345-6789',
            address='45 Ocean Drive, Miami, FL',
            role='customer',
            is_active=True
        )
        user3.set_password('password123')
        db.session.add(user3)

        db.session.commit()

        # Bank Accounts
        acc1 = Account(
            user_id=user1.id,
            account_number='1001234567',
            account_type='Savings',
            balance=Decimal('18450.00'),
            status='Active'
        )
        acc1_checking = Account(
            user_id=user1.id,
            account_number='2001234568',
            account_type='Current',
            balance=Decimal('3500.00'),
            status='Active'
        )

        acc2 = Account(
            user_id=user2.id,
            account_number='1009876543',
            account_type='Current',
            balance=Decimal('9320.50'),
            status='Active'
        )

        acc3 = Account(
            user_id=user3.id,
            account_number='1005544332',
            account_type='Savings',
            balance=Decimal('4200.00'),
            status='Active'
        )

        db.session.add_all([acc1, acc1_checking, acc2, acc3])
        db.session.commit()

        print("Seeding Transaction History...")
        now = datetime.now(timezone.utc)

        txns = [
            Transaction(
                reference_id='TXN-INIT-001',
                account_id=acc1.id,
                transaction_type='DEPOSIT',
                amount=Decimal('15000.00'),
                balance_after=Decimal('15000.00'),
                description='Account Opening Initial Wire Deposit',
                status='COMPLETED',
                timestamp=now - timedelta(days=90)
            ),
            Transaction(
                reference_id='TXN-DEP-102',
                account_id=acc1.id,
                transaction_type='DEPOSIT',
                amount=Decimal('5200.00'),
                balance_after=Decimal('20200.00'),
                description='Monthly Corporate Payroll Credit',
                status='COMPLETED',
                timestamp=now - timedelta(days=60)
            ),
            Transaction(
                reference_id='TXN-WTH-203',
                account_id=acc1.id,
                transaction_type='WITHDRAWAL',
                amount=Decimal('800.00'),
                balance_after=Decimal('19400.00'),
                description='Branch Cash ATM Withdrawal',
                status='COMPLETED',
                timestamp=now - timedelta(days=45)
            ),
            Transaction(
                reference_id='TXN-TRF-304',
                account_id=acc1.id,
                transaction_type='TRANSFER_SENT',
                amount=Decimal('1450.00'),
                balance_after=Decimal('17950.00'),
                description='Transfer to Jane Smith (Acc: #1009876543) - Consulting invoice',
                sender_account_number='1001234567',
                receiver_account_number='1009876543',
                status='COMPLETED',
                timestamp=now - timedelta(days=20)
            ),
            Transaction(
                reference_id='TXN-DEP-405',
                account_id=acc1.id,
                transaction_type='DEPOSIT',
                amount=Decimal('1500.00'),
                balance_after=Decimal('19450.00'),
                description='Client Consulting Retainer Deposit',
                status='COMPLETED',
                timestamp=now - timedelta(days=10)
            ),
            Transaction(
                reference_id='TXN-WTH-506',
                account_id=acc1.id,
                transaction_type='WITHDRAWAL',
                amount=Decimal('1000.00'),
                balance_after=Decimal('18450.00'),
                description='Travel Expenses Withdrawal',
                status='COMPLETED',
                timestamp=now - timedelta(days=2)
            ),
            Transaction(
                reference_id='TXN-INIT-002',
                account_id=acc1_checking.id,
                transaction_type='DEPOSIT',
                amount=Decimal('3500.00'),
                balance_after=Decimal('3500.00'),
                description='Current Account Opening Deposit',
                status='COMPLETED',
                timestamp=now - timedelta(days=30)
            ),
            Transaction(
                reference_id='TXN-INIT-003',
                account_id=acc2.id,
                transaction_type='DEPOSIT',
                amount=Decimal('7870.50'),
                balance_after=Decimal('7870.50'),
                description='Initial Account Opening Deposit',
                status='COMPLETED',
                timestamp=now - timedelta(days=80)
            ),
            Transaction(
                reference_id='TXN-TRF-304-R',
                account_id=acc2.id,
                transaction_type='TRANSFER_RECEIVED',
                amount=Decimal('1450.00'),
                balance_after=Decimal('9320.50'),
                description='Transfer from Johnathan Doe (Acc: #1001234567) - Consulting invoice',
                sender_account_number='1001234567',
                receiver_account_number='1009876543',
                status='COMPLETED',
                timestamp=now - timedelta(days=20)
            ),
            Transaction(
                reference_id='TXN-INIT-004',
                account_id=acc3.id,
                transaction_type='DEPOSIT',
                amount=Decimal('4200.00'),
                balance_after=Decimal('4200.00'),
                description='Initial Account Opening Deposit',
                status='COMPLETED',
                timestamp=now - timedelta(days=40)
            ),
        ]

        db.session.add_all(txns)

        print("Seeding Notifications...")
        notifs = [
            Notification(
                user_id=user1.id,
                title='Welcome to Apex Global Bank!',
                message='Your new Savings Account #1001234567 is officially active and ready for transactions.',
                type='success',
                is_read=True,
                created_at=now - timedelta(days=90)
            ),
            Notification(
                user_id=user1.id,
                title='Deposit Confirmed',
                message='$5,200.00 credited via Corporate Payroll. Ref: TXN-DEP-102.',
                type='info',
                is_read=True,
                created_at=now - timedelta(days=60)
            ),
            Notification(
                user_id=user1.id,
                title='Transfer Sent Successfully',
                message='You transferred $1,450.00 to Jane Smith (#1009876543).',
                type='warning',
                is_read=False,
                created_at=now - timedelta(days=20)
            ),
            Notification(
                user_id=user2.id,
                title='Incoming Fund Transfer',
                message='You received $1,450.00 from Johnathan Doe (#1001234567).',
                type='success',
                is_read=False,
                created_at=now - timedelta(days=20)
            )
        ]
        db.session.add_all(notifs)

        db.session.commit()
        print("Database seeding completed successfully without deprecation warnings!")
        print("--------------------------------------------------")
        print("Admin Login:     admin / admin123")
        print("Customer Login:  john_doe / password123")
        print("Customer 2:      jane_smith / password123")
        print("Customer 3:      robert_brown / password123")
        print("--------------------------------------------------")

if __name__ == '__main__':
    seed_database()
