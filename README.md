# 🏛️ Apex Global Bank — Modern Banking Management System

> **⚠️ Educational Project Disclaimer:**  
> This software is an **educational banking simulation and demonstration project** created for academic, training, and portfolio purposes. It is **not** a real financial institution, does not connect to real financial networks, and should not be used as a production banking system.

A full-stack, responsive, and secure **Banking Management System** engineered with **Python Flask**, **SQLite / MySQL**, **HTML5/CSS3/Bootstrap 5**, **Font Awesome 6**, and **Chart.js**.

Designed with a **dark navy (`#0a192f`) & electric sapphire blue (`#2563eb`)** visual aesthetic, complete with virtual debit cards, real-time balance calculations, atomic inter-account fund transfers, audit ledger surveillance, and PDF statement/receipt generation.

---

## 🌟 Key Features

### 1. 🎨 Modern Design & UI/UX
- **Palette**: Deep Navy (`#0a192f`, `#0f2b5c`), Sapphire Blue (`#1e40af`, `#2563eb`), Cyan accents (`#38bdf8`), and clean whites.
- **Responsive Layout**: Persistent navigation sidebar on desktop, responsive drawer on tablet/mobile with hamburger trigger.
- **Interactive Virtual Card**: Realistic debit/checking card preview with holographic chip, contactless icon, account number copy-to-clipboard, and live balance.
- **Dynamic Cashflow Charts**: Line and doughnut charts powered by **Chart.js** displaying past 6-month inflow (deposits) vs outflow (withdrawals).
- **Micro-Interactions**: Auto-dismissing alerts, real-time live clock, smooth card hover elevations, and status badges.

### 2. 🔐 Authentication & Security Hardening
- **Customer & Admin Roles**: Isolated portal environments (`/customer/*` and `/admin/*`).
- **Cryptographic Security**: Password hashing with Werkzeug (`pbkdf2:sha256`). Plain text passwords are never stored.
- **CSRF Defense**: Cryptographically random `_csrf_token` generation and verification on all mutating requests (`POST`), with secure fallback and security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`).
- **Session Protection**: `HTTPOnly` and `SameSite=Lax` cookie configuration.
- **Registration**: Form validation (alphanumeric usernames, email regex, password strength, terms check, and minimum initial opening deposit of $25.00).
- **Route Protection**: Custom Python decorators (`@login_required`, `@customer_required`, and `@admin_required`) protecting all dashboard endpoints with active user validation.

### 3. 💳 Customer Banking Operations
- **Account Management**:
  - Automatically generates unique 10-digit account numbers (e.g., `100-123-4567`).
  - Multi-account portfolio: Customers can open additional **Savings** or **Current** accounts.
  - Profile management: Update full name, contact phone, and address.
  - Password change with old password verification.
- **Deposit Money**:
  - Deposit funds into any owned active account.
  - Quick amount presets (`+$50`, `+$100`, `+$250`, `+$500`, `+$1,000`, `+$5,000`).
  - Real-time prospective balance calculator.
  - Instant transaction ledger entry and notification.
- **Withdraw Money**:
  - Real-time overdraft safeguards: Prevents any withdrawal exceeding the available account balance.
  - Automated balance update and withdrawal receipt generation.
- **Inter-Account Money Transfer**:
  - **Live AJAX Account Lookup**: As the sender types a 10-digit recipient account number, the system verifies the recipient's name and account status before submission.
  - **Atomic Transaction Commit**: Uses strict database transaction rollback on any failure—ensuring money is never lost or partially transferred.
  - Synchronous generation of outgoing debit transaction for the sender and incoming credit transaction for the recipient.
  - Automated in-app notification dispatch to both parties.
- **Transaction History & Ledger**:
  - Filterable by account, transaction type (Deposits, Withdrawals, Transfers), search keyword, and date range.
  - Individual receipt view with printable template and one-click PDF voucher download.
- **Official Account Statements**:
  - Custom date range selection.
  - High-resolution, professional PDF generation using **ReportLab** containing bank headers, customer details, opening balance, itemized transactions, and legal disclaimers.

### 4. 🛡️ Administrator Control Center
- **Executive Metrics**:
  - Total Bank Liquidity & Reserves.
  - Cumulative Deposits & Withdrawals.
  - Total Registered Customers & Active Bank Accounts.
  - Today's live transaction counter.
- **Customer Management**:
  - Search customers by Name, Email, Username, or Account Number.
  - Detailed **Customer 360** profile view showing all customer accounts, balances, and transaction history.
  - One-click Customer Activation / Deactivation.
- **Bank Accounts Management**:
  - Global accounts ledger.
  - Instant Freeze / Suspend / Reactivate controls for any individual account.
- **Master Audit Ledger**:
  - Surveillance log of all transactions across all customer accounts with full routing details (`Sender Acc -> Receiver Acc`).

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.10+ / Flask 3.x |
| **ORM & Database** | Flask-SQLAlchemy 3.x / SQLite (Zero-config default) or MySQL |
| **Security & Hashing**| Werkzeug Security (`generate_password_hash`, `check_password_hash`), Session CSRF |
| **PDF Generation** | ReportLab 4.x / 5.x |
| **Frontend Framework**| HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3 |
| **Data Visualization**| Chart.js 4.4 |
| **Iconography & Fonts**| Font Awesome 6.5.1, Inter Web Font |

---

## 📁 Project Structure

```
c:\banking management system\
│
├── app.py                      # Application factory, CSRF protection, security headers, error handlers
├── config.py                   # Configuration (Secret key, SQLite/MySQL DB URI, constants)
├── models.py                   # SQLAlchemy Models: User, Account, Transaction, Notification
├── seed.py                     # Database population script with sample data
├── test_app.py                 # Automated 14-point test suite
├── audit_system.py             # Security, access control, and financial edge-case audit script
├── requirements.txt            # Python dependencies
├── README.md                   # System documentation
│
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py          # /login, /register, /admin/login, /logout
│   ├── customer_routes.py      # /customer/dashboard, /deposit, /withdraw, /transfer, /statement
│   ├── admin_routes.py         # /admin/dashboard, /customers, /accounts, /transactions
│   └── api_routes.py           # /api/account/lookup, /api/notifications/*
│
├── utils/
│   ├── __init__.py
│   ├── decorators.py           # @login_required, @admin_required, @customer_required
│   ├── helpers.py              # Account generator, reference generator, notifications
│   └── pdf_generator.py        # ReportLab PDF statement & receipt rendering
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom theme (Navy & Blue, virtual card, tables, stat cards)
│   └── js/
│       ├── main.js             # Sidebar toggler, auto-dismiss alerts, live clock, clipboard
│       ├── dashboard.js        # Chart.js line & cashflow graphs
│       └── transfer.js         # Real-time recipient lookup & balance calculation
│
└── templates/
    ├── base.html               # Master layout with responsive sidebar and topbar
    ├── auth/
    │   ├── login.html          # Split-screen modern login with demo autofill
    │   ├── register.html       # Customer onboarding with initial deposit
    │   └── admin_login.html    # Dedicated high-security admin gateway
    ├── customer/
    │   ├── dashboard.html      # Virtual card, stat cards, chart, quick actions, recent ledger
    │   ├── accounts.html       # Portfolio accounts list & open new account modal
    │   ├── deposit.html        # Cash deposit with quick presets & balance preview
    │   ├── withdraw.html       # Withdrawal with overdraft prevention
    │   ├── transfer.html       # Money transfer with real-time receiver lookup
    │   ├── transactions.html   # Full history ledger with multi-parameter filter
    │   ├── statement.html      # Statement preview & PDF download
    │   ├── receipt.html        # Printable transaction voucher
    │   ├── profile.html        # Personal info update & password change
    │   └── notifications.html  # In-app notifications list
    ├── admin/
    │   ├── dashboard.html      # Admin overview, liquidity stats, doughnut chart
    │   ├── customers.html      # Customer directory with status toggle
    │   ├── customer_detail.html# Customer 360 overview & accounts control
    │   ├── accounts.html       # Global accounts with freeze/activate
    │   └── transactions.html   # Master audit ledger
    └── errors/
        ├── 403.html            # Access forbidden
        ├── 404.html            # Not found
        └── 500.html            # Internal server error
```

---

## 🚀 Setup & Execution Instructions

### 1. Prerequisites
Ensure you have **Python 3.10+** installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
python seed.py
```

### 4. Run Automated Test Suite
```bash
python test_app.py
```

### 5. Run Security & Compliance Audit
```bash
python audit_system.py
```

### 6. Launch the Application
```bash
python app.py
```
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Sample Test Credentials for Educational Testing

| Role | Username / Identifier | Password | Associated Accounts & Details |
|---|---|---|---|
| **System Admin** | `admin` | `admin123` | Master control console, customer management, reserve analytics |
| **Primary Customer** | `john_doe` | `password123` | **Savings**: `#1001234567` ($18,450.00)<br>**Current**: `#2001234568` ($3,500.00) |
| **Secondary Customer** | `jane_smith` | `password123` | **Current**: `#1009876543` ($9,320.50) — *ideal for testing transfers* |
| **Tertiary Customer** | `robert_brown` | `password123` | **Savings**: `#1005544332` ($4,200.00) |

*(Note: On the login screen, click the **"Customer"** or **"Admin"** helper buttons to autofill credentials in 1 click!)*
#   B a n k i n g - m a n a g e m e n t - s y s t e m  
 