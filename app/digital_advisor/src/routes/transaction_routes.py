# backend/app/routes/transaction_routes.py

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from src.services import transaction_service as ts
from src.schemas.transaction_schema import TransactionSchema
from src.extensions import db

transaction_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

transaction_schema = TransactionSchema()
transaction_list_schema = TransactionSchema(many=True)

@transaction_bp.route('', methods=['GET'])
@jwt_required()
def get_user_transactions():
    """
    Retrieves a list of all transactions for the authenticated user.
    Ordered by most recent first.
    """
    user_id = int(get_jwt_identity())
    try:
        transactions = ts.get_transactions_by_user(user_id)
        result = transaction_list_schema.dump(transactions)
        return jsonify(transactions=result), 200
    except Exception as e:
        print(f"Error fetching transactions for user {user_id}: {e}")
        return jsonify({'msg': 'Failed to retrieve transactions. Please try again later.'}), 500
