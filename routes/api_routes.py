from flask import Blueprint, request, jsonify, session
from models import db, Account, User, Notification
from utils.decorators import login_required

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/account/lookup')
@login_required
def lookup_account():
    account_number = request.args.get('account_number', '').strip().replace('-', '')
    current_user_id = session.get('user_id')

    if not account_number or len(account_number) < 5:
        return jsonify({'found': False, 'message': 'Account number is too short.'}), 400

    account = Account.query.filter_by(account_number=account_number).first()

    if not account:
        return jsonify({'found': False, 'message': 'Account not found in system.'}), 404

    is_own_account = (account.user_id == current_user_id)
    
    return jsonify({
        'found': True,
        'account_number': account.account_number,
        'formatted_number': account.formatted_account_number,
        'account_type': account.account_type,
        'holder_name': account.user.full_name,
        'status': account.status,
        'is_active': account.status == 'Active',
        'is_own': is_own_account
    })


@api_bp.route('/notifications/unread-count')
@login_required
def unread_notifications_count():
    user_id = session.get('user_id')
    count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({'unread_count': count})


@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user_id = session.get('user_id')
    notif = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Notification not found'}), 404

