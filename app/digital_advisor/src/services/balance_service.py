# backend/src/services/balance_service.py

from src.extensions import db
from src.models.user import User
from src.services import transaction_service as ts # Import the new transaction service

# --- Cash Management ---

def deposit_funds(user_id: int, amount: float):
    """
    Increases user's cash balance and records a deposit transaction.
    """
    if amount <= 0:
        raise ValueError("Deposit amount must be greater than zero.")

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise ValueError("User not found.")

    with db.session.begin_nested():
        # 1. Update user balance
        user.balance += amount
        db.session.add(user)

        # 2. Record the deposit transaction
        ts.create_transaction(
            user_id=user_id,
            transaction_type='DEPOSIT',
            volume=amount,          # The amount of cash deposited
            price_per_unit=1.0,     # Price per unit for cash is 1.0
            ticker=None             # No ticker for cash transactions
        )

    db.session.commit()
    return user.balance


def withdraw_funds(user_id: int, amount: float):
    """
    Decreases user's cash balance and records a withdrawal transaction.
    """
    if amount <= 0:
        raise ValueError("Withdrawal amount must be greater than zero.")

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    if user.balance < amount:
        raise ValueError(f"Insufficient balance. Requested: {amount:.2f}, Available: {user.balance:.2f}")

    with db.session.begin_nested():
        # 1. Update user balance
        user.balance -= amount
        db.session.add(user)

        # 2. Record the withdrawal transaction
        ts.create_transaction(
            user_id=user_id,
            transaction_type='WITHDRAW',
            volume=amount,          # The amount of cash withdrawn
            price_per_unit=1.0,     # Price per unit for cash is 1.0
            ticker=None             # No ticker for cash transactions
        )

    db.session.commit()
    return user.balance

