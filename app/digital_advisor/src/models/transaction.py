# backend/app/models/transaction.py

from src.extensions import db
import datetime
from sqlalchemy import Computed # Import Computed from SQLAlchemy

class Transaction(db.Model):
    """
    Represents a financial transaction made by a user (e.g., buy/sell of an asset, deposit/withdrawal).
    """
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    ticker = db.Column(db.String(8), nullable=True) 
    transaction_type = db.Column(db.String(10), nullable=False) 
    volume = db.Column(db.Float, nullable=False) 
    price_per_unit = db.Column(db.Float, nullable=False)
    
    # --- FIX HERE: Use db.Computed for generated columns ---
    # The expression 'volume * price_per_unit' should match exactly what's in your DB's GENERATED ALWAYS AS (...)
    # persisted=True maps to STORED in PostgreSQL. If your column is VIRTUAL, use persisted=False.
    total_amount = db.Column(
        db.Float, 
        Computed("volume * price_per_unit", persisted=True), 
        nullable=False
    )
    # --- END FIX ---
    
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)

    # Relationship to user
    user = db.relationship('User', back_populates='transactions', lazy=True)

    def __repr__(self):
        # Note: self.total_amount will be populated by the DB after commit/refresh
        return (f'<Transaction {self.transaction_id}: User {self.user_id} - '
                f'{self.transaction_type.upper()} {self.volume} of {self.ticker or "CASH"} '
                f'at {self.price_per_unit} each. Total: {self.total_amount}>')