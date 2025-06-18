import pytest
from flask import Flask
from src.extensions import db as _db
from src.models.user import User # Import your User model
from src.routes.auth_routes import auth_bp
from src.routes.balance_routes import balance_bp
from src.routes.transaction_routes import transaction_bp
from src.routes.prediction_routes import prediction_bp
from src.schemas.user_schema import UserSchema, UserRegisterSchema, UserLoginSchema
from flask_jwt_extended import JWTManager

@pytest.fixture(scope='session') 
def app():
    app = Flask(__name__)
    app.config.from_mapping(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY='super-secret'
        # Add dummy config for prediction if needed.
        # E.g., for COMPANIES_TYPE1/2 and model directories, though we'll mock these more precisely.
        # If you have an app.config.py, you might just configure app.config['COMPANIES_TYPE1'] = [...]
        # or rely on direct mocking within tests.
    )

    _db.init_app(app)
    JWTManager(app)

    with app.app_context():
        app.register_blueprint(auth_bp)
        app.register_blueprint(balance_bp)
        app.register_blueprint(transaction_bp)
        app.register_blueprint(prediction_bp)

        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Fixture for creating a test client."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """Fixture for creating a test runner."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """Fixture for providing a database session."""
    with app.app_context():
        _db.session.begin_nested() # Use nested transaction for rollback
        yield _db
        _db.session.rollback() # Rollback changes after each test