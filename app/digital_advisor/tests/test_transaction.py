import pytest
from unittest.mock import patch, MagicMock
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError
import datetime

# Import necessary components from your application
from src.extensions import db
from src.models.user import User
from src.models.transaction import Transaction
from src.schemas.transaction_schema import TransactionSchema
from src.services import transaction_service as ts


# --- Fixtures ---

@pytest.fixture
def mock_user_transaction_tests(app, db):
    """
    Fixture to create a user for transaction-related tests.
    Ensures a clean user in the DB for each test.
    """
    with app.app_context():
        user = User(username='transaction_user', email='transaction@example.com')
        user.set_password('password123')
        user.balance = 1000.0 # Give some balance if needed for future tests
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        yield user
        db.session.delete(user)
        db.session.commit()

@pytest.fixture
def logged_in_client_transaction_tests(client, app, db, mock_user_transaction_tests):
    """
    Fixture to get a Flask test client with a JWT token for the mock_user_transaction_tests.
    """
    with app.app_context():
        access_token = create_access_token(identity=str(mock_user_transaction_tests.user_id))
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        yield client, mock_user_transaction_tests, headers


# --- Test Section 1: Schema Tests (from app.schemas.transaction_schema) ---

def test_transaction_schema_serialization():
    """Test dumping a Transaction object to a dictionary."""
    now = datetime.datetime.utcnow()
    transaction_data = {
        'transaction_id': 1,
        'user_id': 101,
        'ticker': 'GOOG',
        'transaction_type': 'BUY',
        'volume': 10.5,
        'price_per_unit': 150.0,
        'total_amount': 1575.0, # This would be computed by DB, but for dump we provide it
        'timestamp': now
    }
    schema = TransactionSchema()
    result = schema.dump(transaction_data)

    assert result['transaction_id'] == 1
    assert result['user_id'] == 101
    assert result['ticker'] == 'GOOG'
    assert result['transaction_type'] == 'BUY'
    assert result['volume'] == 10.5
    assert result['price_per_unit'] == 150.0
    assert result['total_amount'] == 1575.0
    assert 'timestamp' in result # Check for presence, not exact match of datetime object


@pytest.mark.parametrize("invalid_type", ["INVALID", "DEPO", "WITH"])
def test_transaction_schema_invalid_transaction_type(invalid_type):
    """Test schema validation for invalid transaction types."""
    schema = TransactionSchema()
    data = {
        'ticker': 'AAPL',
        'transaction_type': invalid_type,
        'volume': 5.0,
        'price_per_unit': 170.0
    }
    with pytest.raises(ValidationError) as excinfo:
        schema.load(data)
    # Changed assertion: Look for the core message without the full list formatting
    assert "Must be one of: BUY, SELL, DEPOSIT, WITHDRAW" in str(excinfo.value)


@pytest.mark.parametrize("invalid_volume", [0, -10, -0.0001])
def test_transaction_schema_invalid_volume(invalid_volume):
    """Test schema validation for invalid volume (<= 0)."""
    schema = TransactionSchema()
    data = {
        'ticker': 'MSFT',
        'transaction_type': 'BUY',
        'volume': invalid_volume,
        'price_per_unit': 250.0
    }
    with pytest.raises(ValidationError) as excinfo:
        schema.load(data)
    assert "Must be greater than or equal to 0.0001" in str(excinfo.value)

@pytest.mark.parametrize("invalid_price", [0, -10, -0.0001])
def test_transaction_schema_invalid_price_per_unit(invalid_price):
    """Test schema validation for invalid price_per_unit (<= 0)."""
    schema = TransactionSchema()
    data = {
        'ticker': 'MSFT',
        'transaction_type': 'BUY',
        'volume': 10.0,
        'price_per_unit': invalid_price
    }
    with pytest.raises(ValidationError) as excinfo:
        schema.load(data)
    assert "Must be greater than or equal to 0.0001" in str(excinfo.value)

def test_transaction_schema_ticker_allows_none_for_cash_transactions():
    """Test that ticker can be None for DEPOSIT/WITHDRAW."""
    schema = TransactionSchema()
    data = {
        'ticker': None, # explicitly None
        'transaction_type': 'DEPOSIT',
        'volume': 500.0,
        'price_per_unit': 1.0
    }
    result = schema.load(data)
    assert result['ticker'] is None
    assert result['transaction_type'] == 'DEPOSIT'


# --- Test Section 2: Transaction Service Tests (from app.services.transaction_service) ---

def test_create_transaction_success(mock_user_transaction_tests, app, db):
    """Test successful creation of a transaction."""
    user_id = mock_user_transaction_tests.user_id
    with app.app_context():
        transaction = ts.create_transaction(
            user_id=user_id,
            transaction_type='BUY',
            volume=5.0,
            price_per_unit=120.0,
            ticker='TSLA'
        )
        db.session.commit() # Commit to populate generated columns and persist

        # Refresh the object to get computed fields from DB
        db.session.refresh(transaction)

        assert transaction.transaction_id is not None
        assert transaction.user_id == user_id
        assert transaction.ticker == 'TSLA'
        assert transaction.transaction_type == 'BUY'
        assert transaction.volume == 5.0
        assert transaction.price_per_unit == 120.0
        assert transaction.total_amount == 5.0 * 120.0 # Verify computed value
        assert transaction.timestamp is not None

        # Verify it's in the database
        retrieved_transaction = db.session.get(Transaction, transaction.transaction_id)
        assert retrieved_transaction == transaction

def test_create_transaction_cash_deposit_success(mock_user_transaction_tests, app, db):
    """Test successful creation of a cash deposit transaction."""
    user_id = mock_user_transaction_tests.user_id
    with app.app_context():
        transaction = ts.create_transaction(
            user_id=user_id,
            transaction_type='DEPOSIT',
            volume=500.0,
            price_per_unit=1.0,
            ticker=None # No ticker for cash
        )
        db.session.commit()
        db.session.refresh(transaction)

        assert transaction.transaction_id is not None
        assert transaction.user_id == user_id
        assert transaction.ticker is None
        assert transaction.transaction_type == 'DEPOSIT'
        assert transaction.volume == 500.0
        assert transaction.price_per_unit == 1.0
        assert transaction.total_amount == 500.0 * 1.0
        assert transaction.timestamp is not None

def test_create_transaction_invalid_volume():
    """Test create_transaction with zero or negative volume."""
    with pytest.raises(ValueError, match="Transaction volume/amount must be greater than zero."):
        ts.create_transaction(user_id=1, transaction_type='BUY', volume=0, price_per_unit=100.0, ticker='AAPL')
    with pytest.raises(ValueError, match="Transaction volume/amount must be greater than zero."):
        ts.create_transaction(user_id=1, transaction_type='SELL', volume=-10, price_per_unit=50.0, ticker='MSFT')

def test_create_transaction_invalid_price_per_unit():
    """Test create_transaction with zero or negative price_per_unit."""
    with pytest.raises(ValueError, match="Transaction price per unit must be greater than zero."):
        ts.create_transaction(user_id=1, transaction_type='DEPOSIT', volume=100, price_per_unit=0, ticker=None)
    with pytest.raises(ValueError, match="Transaction price per unit must be greater than zero."):
        ts.create_transaction(user_id=1, transaction_type='WITHDRAW', volume=50, price_per_unit=-5, ticker=None)

def test_create_transaction_invalid_type():
    """Test create_transaction with an invalid transaction type."""
    with pytest.raises(ValueError, match="Invalid transaction type."):
        ts.create_transaction(user_id=1, transaction_type='INVALID_TYPE', volume=1, price_per_unit=1, ticker=None)

def test_get_transactions_by_user_multiple(mock_user_transaction_tests, app, db):
    """Test retrieving multiple transactions for a user, ordered correctly."""
    user_id = mock_user_transaction_tests.user_id
    with app.app_context():
        # Create a few transactions
        tx1 = ts.create_transaction(user_id=user_id, transaction_type='DEPOSIT', volume=100, price_per_unit=1)
        # Simulate a slight time difference for ordering
        db.session.commit()
        db.session.refresh(tx1) # Populate total_amount and timestamp
        import time; time.sleep(0.01) # Small delay for distinct timestamps
        tx2 = ts.create_transaction(user_id=user_id, transaction_type='BUY', volume=5, price_per_unit=200, ticker='AMZN')
        db.session.commit()
        db.session.refresh(tx2)
        time.sleep(0.01)
        tx3 = ts.create_transaction(user_id=user_id, transaction_type='SELL', volume=2, price_per_unit=210, ticker='AMZN')
        db.session.commit()
        db.session.refresh(tx3)

        transactions = ts.get_transactions_by_user(user_id)

        assert len(transactions) == 3
        # Assert order (most recent first)
        assert transactions[0].transaction_id == tx3.transaction_id
        assert transactions[1].transaction_id == tx2.transaction_id
        assert transactions[2].transaction_id == tx1.transaction_id

def test_get_transactions_by_user_no_transactions(mock_user_transaction_tests, app):
    """Test retrieving transactions for a user with no transactions."""
    user_id = mock_user_transaction_tests.user_id
    with app.app_context():
        transactions = ts.get_transactions_by_user(user_id)
        assert len(transactions) == 0

def test_get_transactions_by_user_other_user_transactions(mock_user_transaction_tests, app, db):
    """
    Test that a user only retrieves their own transactions, not others'.
    """
    user_id = mock_user_transaction_tests.user_id
    with app.app_context():
        # Create a transaction for mock_user
        ts.create_transaction(user_id=user_id, transaction_type='DEPOSIT', volume=100, price_per_unit=1)
        # Create another user and a transaction for them
        other_user = User(username='other_user', email='other@example.com')
        other_user.set_password('pass')
        db.session.add(other_user)
        db.session.commit()
        db.session.refresh(other_user)
        ts.create_transaction(user_id=other_user.user_id, transaction_type='BUY', volume=1, price_per_unit=10, ticker='XYZ')
        db.session.commit()

        transactions = ts.get_transactions_by_user(user_id)
        assert len(transactions) == 1
        assert transactions[0].user_id == user_id

# --- Test Section 3: Transaction Blueprint (Route) Tests (from app.routes.transaction_routes) ---

def test_get_user_transactions_route_success(logged_in_client_transaction_tests, app, db):
    """Test the GET /transactions route successfully retrieves a user's transactions."""
    client, user, headers = logged_in_client_transaction_tests
    user_id = user.user_id

    # Create some transactions directly via service (they'll be committed)
    with app.app_context():
        tx1 = ts.create_transaction(user_id=user_id, transaction_type='DEPOSIT', volume=100, price_per_unit=1)
        db.session.commit()
        db.session.refresh(tx1)
        import time; time.sleep(0.01) # Simulate time difference
        tx2 = ts.create_transaction(user_id=user_id, transaction_type='BUY', volume=2, price_per_unit=50, ticker='TEST')
        db.session.commit()
        db.session.refresh(tx2)

        # Mock the service layer, as we're testing the route's interaction with the service
        # and serialization, not the service's internal DB logic.
        # It's okay to patch the service and then provide *real* objects,
        # as long as those objects are what the service *would* return.
        with patch('src.routes.transaction_routes.ts.get_transactions_by_user') as mock_get_transactions:
            mock_get_transactions.return_value = [tx2, tx1] # Ensure order for assertion

            response = client.get('/transactions', headers=headers)
            assert response.status_code == 200
            data = response.json['transactions']
            assert len(data) == 2

            # Assert order and content of returned data
            assert data[0]['transaction_id'] == tx2.transaction_id
            assert data[0]['ticker'] == 'TEST'
            assert data[0]['transaction_type'] == 'BUY'
            assert data[0]['volume'] == 2.0
            assert data[0]['price_per_unit'] == 50.0
            assert data[0]['total_amount'] == 100.0 # 2 * 50

            assert data[1]['transaction_id'] == tx1.transaction_id
            assert data[1]['ticker'] is None
            assert data[1]['transaction_type'] == 'DEPOSIT'
            assert data[1]['volume'] == 100.0
            assert data[1]['price_per_unit'] == 1.0
            assert data[1]['total_amount'] == 100.0 # 100 * 1

            mock_get_transactions.assert_called_once_with(user_id)

def test_get_user_transactions_route_no_transactions(logged_in_client_transaction_tests):
    """Test the GET /transactions route when a user has no transactions."""
    client, user, headers = logged_in_client_transaction_tests
    user_id = user.user_id

    with patch('src.routes.transaction_routes.ts.get_transactions_by_user') as mock_get_transactions:
        mock_get_transactions.return_value = [] # Simulate no transactions

        response = client.get('/transactions', headers=headers)
        assert response.status_code == 200
        assert response.json['transactions'] == []
        mock_get_transactions.assert_called_once_with(user_id)

def test_get_user_transactions_route_unauthenticated(client):
    """Test the GET /transactions route without authentication."""
    response = client.get('/transactions')
    assert response.status_code == 401
    assert 'Missing Authorization Header' in response.json['msg']

def test_get_user_transactions_route_service_error(logged_in_client_transaction_tests):
    """Test the GET /transactions route when the service encounters an error."""
    client, user, headers = logged_in_client_transaction_tests
    user_id = user.user_id

    with patch('src.routes.transaction_routes.ts.get_transactions_by_user') as mock_get_transactions:
        mock_get_transactions.side_effect = Exception("Database read error")

        response = client.get('/transactions', headers=headers)
        assert response.status_code == 500
        assert response.json['msg'] == 'Failed to retrieve transactions. Please try again later.'
        mock_get_transactions.assert_called_once_with(user_id)