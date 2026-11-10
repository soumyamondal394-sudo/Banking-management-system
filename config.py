import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'apex-secure-banking-system-secret-key-2026')
    # Default to SQLite for zero-config portable execution, can be swapped with MySQL by setting DATABASE_URL
    # e.g., mysql+pymysql://user:password@localhost/banking_db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(BASE_DIR, 'banking.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Banking specific configurations
    BANK_NAME = "Apex Global Bank"
    BANK_CODE = "APEX"
    CURRENCY_SYMBOL = "$"
    MIN_INITIAL_DEPOSIT = 25.00
    DAILY_TRANSFER_LIMIT = 50000.00

