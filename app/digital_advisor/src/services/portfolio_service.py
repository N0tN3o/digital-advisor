# backend/src/services/portfolio_service.py

from src.extensions import db
from src.models.user import User
from src.models.portfolio import Portfolio
from src.services import transaction_service as ts # Import the new transaction service

# --- Portfolio Querying ---

def get_portfolio_by_user(user_id: int):
    """
    Retrieves all asset holdings for a given user.
    """
    return Portfolio.query.filter_by(user_id=user_id).all()


# --- Buy Logic ---

def buy_ticker(user_id: int, ticker: str, volume: float, price_per_unit: float):
    """
    Handles the purchase of an asset, updating the user's cash balance
    and portfolio holdings, and recording the transaction.
    """
    if volume <= 0:
        raise ValueError("Buy volume must be greater than zero.")
    if price_per_unit <= 0:
        raise ValueError("Price per unit must be greater than zero.")

    total_cost = volume * price_per_unit

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    if user.balance < total_cost:
        raise ValueError(f"Insufficient funds. Required: {total_cost:.2f}, Available: {user.balance:.2f}")

    # Use a nested session to ensure atomicity of all operations (balance update, portfolio update, transaction record)
    with db.session.begin_nested():
        # 1. Update user balance
        user.balance -= total_cost
        db.session.add(user)

        # 2. Update portfolio holdings
        portfolio_entry = Portfolio.query.filter_by(user_id=user_id, ticker=ticker).first()
        if portfolio_entry:
            portfolio_entry.volume += volume
            db.session.add(portfolio_entry)
        else:
            portfolio_entry = Portfolio(
                user_id=user_id,
                ticker=ticker,
                volume=volume
            )
            db.session.add(portfolio_entry)

        # 3. Record the transaction
        # The transaction service adds the transaction to the session, but doesn't commit
        ts.create_transaction(
            user_id=user_id,
            ticker=ticker, # Ticker is passed here
            transaction_type='BUY',
            volume=volume,
            price_per_unit=price_per_unit
        )

    db.session.commit() # Commit all changes from the nested session
    return portfolio_entry, user.balance


# --- Sell Logic ---

def sell_ticker(user_id: int, ticker: str, volume: float, price_per_unit: float):
    """
    Handles the sale of an asset, updating the user's cash balance
    and portfolio holdings, and recording the transaction.
    """
    if volume <= 0:
        raise ValueError("Sell volume must be greater than zero.")
    if price_per_unit <= 0:
        raise ValueError("Price per unit must be greater than zero.")

    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise ValueError("User not found.")

    portfolio_entry = Portfolio.query.filter_by(user_id=user_id, ticker=ticker).first()
    if not portfolio_entry:
        raise ValueError(f"Ticker '{ticker}' not found in user's portfolio.")
    if portfolio_entry.volume < volume:
        raise ValueError(f"Not enough volume of {ticker} to sell. Available: {portfolio_entry.volume:.4f}, Attempted: {volume:.4f}")

    total_revenue = volume * price_per_unit

    # Use a nested session to ensure atomicity of all operations (balance update, portfolio update, transaction record)
    with db.session.begin_nested():
        # 1. Update user balance
        user.balance += total_revenue
        db.session.add(user)

        # 2. Update portfolio holdings
        portfolio_entry.volume -= volume
        if portfolio_entry.volume <= 0:
            db.session.delete(portfolio_entry)
            portfolio_entry = None # Set to None if the holding is removed
        else:
            db.session.add(portfolio_entry)

        # 3. Record the transaction
        # The transaction service adds the transaction to the session, but doesn't commit
        ts.create_transaction(
            user_id=user_id,
            ticker=ticker, # Ticker is passed here
            transaction_type='SELL',
            volume=volume,
            price_per_unit=price_per_unit
        )

    db.session.commit() # Commit all changes from the nested session
    return portfolio_entry, user.balance

