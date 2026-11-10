import secrets
from flask import Flask, render_template, session, request, abort
from config import Config
from models import db, User, Notification
from routes.auth_routes import auth_bp
from routes.customer_routes import customer_bp
from routes.admin_routes import admin_bp
from routes.api_routes import api_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # CSRF Token Generator
    def get_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    # CSRF Protection Hook
    @app.before_request
    def verify_csrf():
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Skip CSRF check only when explicitly disabled in test configuration
            if app.config.get('TESTING') and not app.config.get('CSRF_ENABLED', True):
                return
            token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
            expected_token = session.get('_csrf_token')
            if not token or not expected_token or not secrets.compare_digest(token, expected_token):
                abort(403, description="Security Notice: CSRF token validation failed. Request untrusted.")

    # Global Context Processors
    @app.context_processor
    def inject_global_data():
        unread_notifications = 0
        current_user = None
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
            if current_user:
                unread_notifications = Notification.query.filter_by(
                    user_id=current_user.id,
                    is_read=False
                ).count()

        return {
            'bank_name': app.config.get('BANK_NAME', 'Apex Global Bank'),
            'bank_code': app.config.get('BANK_CODE', 'APEX'),
            'currency_symbol': app.config.get('CURRENCY_SYMBOL', '$'),
            'current_user': current_user,
            'unread_notifications_count': unread_notifications,
            'csrf_token': get_csrf_token
        }

    # Security Headers
    @app.after_request
    def apply_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    # Custom Jinja filters
    @app.template_filter('currency')
    def currency_filter(val):
        try:
            return f"${float(val):,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter('format_acc')
    def format_acc_filter(val):
        s = str(val or '')
        if len(s) == 10:
            return f"{s[:3]}-{s[3:6]}-{s[6:]}"
        return s

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', error_msg=getattr(e, 'description', None)), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Ensure tables are created
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
