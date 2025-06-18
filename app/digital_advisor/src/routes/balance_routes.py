from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from src.schemas.balance_schema import DepositWithdrawSchema
from src.extensions import db  # Required for rollback on exception
from src.services import balance_service as bs


balance_bp = Blueprint('balance', __name__, url_prefix='/balance')

deposit_withdraw_schema = DepositWithdrawSchema()

# --- Cash Management Routes ---

@balance_bp.route('/deposit', methods=['POST'])
@jwt_required()
def deposit_funds_route():
    """
    Allows a user to deposit funds into their main cash balance.
    """
    user_id = int(get_jwt_identity())
    json_data = request.get_json() or {}

    try:
        data = deposit_withdraw_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    amount = data['amount']

    try:
        new_balance = bs.deposit_funds(user_id, amount)
        return jsonify(message='Deposit successful', new_balance=new_balance), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error processing deposit for user {user_id}: {e}")
        return jsonify({'msg': 'An unexpected error occurred during the deposit transaction.'}), 500


@balance_bp.route('/withdraw', methods=['POST'])
@jwt_required()
def withdraw_funds_route():
    """
    Allows a user to withdraw funds from their main cash balance.
    """
    user_id = int(get_jwt_identity())
    json_data = request.get_json() or {}

    try:
        data = deposit_withdraw_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    amount = data['amount']

    try:
        new_balance = bs.withdraw_funds(user_id, amount)
        return jsonify(message='Withdrawal successful', new_balance=new_balance), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error processing withdrawal for user {user_id}: {e}")
        return jsonify({'msg': 'An unexpected error occurred during the withdrawal transaction.'}), 500