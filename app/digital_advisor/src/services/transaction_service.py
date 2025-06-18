# backend/src/services/transaction_service.py

from src.extensions import db
from src.models.transaction import Transaction
from typing import List, Optional

# --- Transaction Creation ---

def create_transaction(
    user_id: int, 
    transaction_type: str, 
    volume: float, 
    price_per_unit: float,
    ticker: Optional[str] = None 
) -> Transaction:
    """
    Records a new transaction in the database.
    total_amount is now a GENERATED ALWAYS column in the DB, so it's not passed explicitly.
    """
    if volume <= 0:
        raise ValueError("Transaction volume/amount must be greater than zero.")
    if price_per_unit <= 0:
        raise ValueError("Transaction price per unit must be greater than zero.")
    
    valid_transaction_types = ['BUY', 'SELL', 'DEPOSIT', 'WITHDRAW']
    if transaction_type not in valid_transaction_types:
        raise ValueError(f"Invalid transaction type. Must be one of {valid_transaction_types}.")

    # --- FIX HERE: DO NOT calculate or pass total_amount to constructor ---
    # The database will calculate total_amount automatically.
    # total_amount = volume * price_per_unit # This line is no longer needed for DB insertion
    # --- END FIX ---

    transaction = Transaction(
        user_id=user_id,
        ticker=ticker,
        transaction_type=transaction_type,
        volume=volume,
        price_per_unit=price_per_unit,
        # Removed total_amount=total_amount from here
    )
    db.session.add(transaction)

    # Note: db.session.commit() is still NOT called here, as transactions
    # are part of larger atomic operations handled by calling services.
    # The total_amount on the 'transaction' object will be populated by SQLAlchemy
    # after the commit (via a database refresh) if you need to access it immediately.

    return transaction

# --- Transaction Querying ---

def get_transactions_by_user(user_id: int) -> List[Transaction]:
    """
    Retrieves all transactions for a given user, ordered by timestamp descending.
    """
    return Transaction.query.filter_by(user_id=user_id).order_by(Transaction.timestamp.desc()).all()

