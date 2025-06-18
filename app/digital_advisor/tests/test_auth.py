import pytest
from unittest.mock import patch, MagicMock
from flask_jwt_extended import create_access_token
from marshmallow import ValidationError

# Import all necessary components from your application
from src.models.user import User
from src.schemas.user_schema import UserSchema, UserRegisterSchema, UserLoginSchema
from src.services.auth_service import (
    validate_registration_data,
    register_user,
    authenticate_user,
    get_user_by_id
)

# --- Test Section 1: User Model Tests ---

def test_user_set_and_check_password():
    user = User(username='testuser_model', email='model@example.com')
    password = 'securepassword_model'
    user.set_password(password)

    assert user.password_hash is not None
    assert user.check_password(password) is True
    assert user.check_password('wrongpassword_model') is False

def test_user_default_balance():
    user = User(username='anotheruser_model', email='anothermodel@example.com')
    user.balance = 0.0
    assert user.balance == 0.0

# --- Test Section 2: Schema Tests ---

def test_user_schema_serialization():
    user_data = {
        'user_id': 1,
        'username': 'testuser_schema',
        'email': 'schema@example.com',
        'balance': 100.0
    }
    schema = UserSchema()
    result = schema.dump(user_data)
    assert result == user_data

def test_user_register_schema_valid_load():
    data = {
        'username': 'newuser_schema',
        'email': 'new_schema@example.com',
        'password': 'verysecurepassword_schema'
    }
    schema = UserRegisterSchema()
    result = schema.load(data)
    assert result['username'] == 'newuser_schema'
    assert result['email'] == 'new_schema@example.com'
    assert 'password' in result

def test_user_register_schema_invalid_email():
    data = {
        'username': 'newuser_schema',
        'email': 'invalid-email',
        'password': 'verysecurepassword_schema'
    }
    schema = UserRegisterSchema()
    with pytest.raises(ValidationError):
        schema.load(data)

def test_user_register_schema_password_too_short():
    data = {
        'username': 'newuser_schema',
        'email': 'new_schema@example.com',
        'password': 'short'
    }
    schema = UserRegisterSchema()
    with pytest.raises(ValidationError):
        schema.load(data)

def test_user_login_schema_valid_load():
    data = {
        'username': 'loginuser_schema',
        'password': 'loginpassword_schema'
    }
    schema = UserLoginSchema()
    result = schema.load(data)
    assert result['username'] == 'loginuser_schema'
    assert 'password' in result

def test_user_login_schema_missing_username():
    data = {
        'password': 'loginpassword_schema'
    }
    schema = UserLoginSchema()
    with pytest.raises(ValidationError):
        schema.load(data)

# --- Test Section 3: Auth Service Tests ---

@pytest.mark.parametrize("username, email, password, expected_error", [
    ("", "test@example.com", "password123", "Username is required"),
    ("user1", "", "password123", "Valid email is required"),
    ("user1", "invalid-email", "password123", "Valid email is required"),
    ("user1", "test@example.com", "", "Password is required"),
    ("user1", "test@example.com", "short", "Password must be at least 8 characters long"),
    ("user1", "test@example.com", "password123", None),
])
def test_validate_registration_data(username, email, password, expected_error):
    error = validate_registration_data(username, email, password)
    assert error == expected_error

@patch('src.extensions.db.session.add')
@patch('src.extensions.db.session.commit')
@patch('src.models.user.User.query')
def test_register_user_success(mock_query, mock_commit, mock_add, app):
    with app.app_context():
        mock_query.filter.return_value.first.return_value = None
        user, err_msg = register_user("newuser_svc", "new_svc@example.com", "securepassword_svc")

        assert err_msg is None
        assert user is not None
        assert user.username == "newuser_svc"
        assert user.email == "new_svc@example.com"
        assert user.balance == 0.0
        mock_add.assert_called_once_with(user)
        mock_commit.assert_called_once()
        assert user.check_password("securepassword_svc")

@patch('src.extensions.db.session.add')
@patch('src.extensions.db.session.commit')
@patch('src.models.user.User.query')
def test_register_user_already_exists(mock_query, mock_commit, mock_add, app):
    with app.app_context():
        mock_user = MagicMock(spec=User)
        mock_query.filter.return_value.first.return_value = mock_user

        user, err_msg = register_user("existinguser_svc", "existing_svc@example.com", "password_svc")

        assert user is None
        assert err_msg == 'User with that username or email already exists'
        mock_add.assert_not_called()
        mock_commit.assert_not_called()

@patch('src.services.auth_service.create_access_token')
@patch('src.models.user.User.query')
def test_authenticate_user_success(mock_query, mock_create_access_token, app):
    with app.app_context():
        mock_user = MagicMock(spec=User)
        mock_user.user_id = 1
        mock_user.check_password.return_value = True
        mock_query.filter_by.return_value.first.return_value = mock_user
        mock_create_access_token.return_value = "mock_jwt_token_svc"

        token, err_msg = authenticate_user("testuser_svc", "correctpassword_svc")

        assert err_msg is None
        assert token == "mock_jwt_token_svc"
        mock_user.check_password.assert_called_once_with("correctpassword_svc")
        mock_create_access_token.assert_called_once_with(identity="1")

@patch('src.models.user.User.query')
def test_authenticate_user_bad_username(mock_query, app):
    with app.app_context():
        mock_query.filter_by.return_value.first.return_value = None

        token, err_msg = authenticate_user("nonexistent_svc", "anypassword_svc")

        assert token is None
        assert err_msg == 'Bad username or password'

@patch('src.models.user.User.query')
def test_authenticate_user_bad_password(mock_query, app):
    with app.app_context():
        mock_user = MagicMock(spec=User)
        mock_user.check_password.return_value = False
        mock_query.filter_by.return_value.first.return_value = mock_user

        token, err_msg = authenticate_user("testuser_svc", "wrongpassword_svc")

        assert token is None
        assert err_msg == 'Bad username or password'
        mock_user.check_password.assert_called_once_with("wrongpassword_svc")

@patch('src.extensions.db.session.get')
def test_get_user_by_id_found(mock_db_get, app):
    with app.app_context():
        mock_user = MagicMock(spec=User)
        mock_db_get.return_value = mock_user

        user = get_user_by_id(1)
        assert user == mock_user
        mock_db_get.assert_called_once_with(User, 1)

@patch('src.extensions.db.session.get')
def test_get_user_by_id_not_found(mock_db_get, app):
    with app.app_context():
        mock_db_get.return_value = None

        user = get_user_by_id(999)
        assert user is None
        mock_db_get.assert_called_once_with(User, 999)

# --- Test Section 4: Auth Blueprint (Routes) ---

def test_auth_route_register_success(client, app, db):
    with patch('src.routes.auth_routes.register_user') as mock_register_user:
        mock_user = MagicMock()
        mock_user.username = "newuser_route"
        mock_user.email = "new_route@example.com"
        mock_register_user.return_value = (mock_user, None)

        response = client.post('/auth/register', json={
            'username': 'newuser_route',
            'email': 'new_route@example.com',
            'password': 'securepassword123_route'
        })
        assert response.status_code == 201
        assert response.json == {'msg': 'User registered successfully'}

def test_auth_route_register_validation_failure(client):
    with patch('src.routes.auth_routes.validate_registration_data') as mock_validate_data:
        mock_validate_data.return_value = "Username or email already taken (route)"
        response = client.post('/auth/register', json={
            'username': 'existinguser_route',
            'email': 'existing_route@example.com',
            'password': 'password123_route'
        })
        assert response.status_code == 400
        assert response.json == {'msg': 'Username or email already taken (route)'}

def test_auth_route_register_user_exists_error(client):
    with patch('src.routes.auth_routes.register_user') as mock_register_user:
        mock_register_user.return_value = (None, 'User with that username or email already exists (route)')
        response = client.post('/auth/register', json={
            'username': 'existinguser_route',
            'email': 'existing_route@example.com',
            'password': 'password123_route'
        })
        assert response.status_code == 409
        assert response.json == {'msg': 'User with that username or email already exists (route)'}

def test_auth_route_login_success(client, app):
    with patch('src.routes.auth_routes.authenticate_user') as mock_authenticate_user:
        mock_authenticate_user.return_value = ("mock_access_token_route", None)
        response = client.post('/auth/login', json={
            'username': 'testuser_route',
            'password': 'password123_route'
        })
        assert response.status_code == 200
        assert response.json == {'access_token': 'mock_access_token_route'}

def test_auth_route_login_authentication_failure(client):
    with patch('src.routes.auth_routes.authenticate_user') as mock_authenticate_user:
        mock_authenticate_user.return_value = (None, 'Bad username or password (route)')
        response = client.post('/auth/login', json={
            'username': 'wronguser_route',
            'password': 'wrongpassword_route'
        })
        assert response.status_code == 401
        assert response.json == {'msg': 'Bad username or password (route)'}

def test_auth_route_get_current_user_success(client, app):
    with app.app_context():
        access_token = create_access_token(identity='1')

    with patch('src.routes.auth_routes.get_user_by_id') as mock_get_user_by_id:
        mock_get_user_by_id.return_value = {
            'user_id': 1,
            'username': 'authenticated_user_route',
            'email': 'auth_route@example.com',
            'balance': 500.0
        }

        response = client.get('/auth/me', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        assert response.json == {
            'user_id': 1,
            'username': 'authenticated_user_route',
            'email': 'auth_route@example.com',
            'balance': 500.0
        }

def test_auth_route_get_current_user_not_found(client, app):
    with app.app_context():
        access_token = create_access_token(identity='999')

    with patch('src.routes.auth_routes.get_user_by_id') as mock_get_user_by_id:
        mock_get_user_by_id.return_value = None

        response = client.get('/auth/me', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert response.json == {'msg': 'User not found'}
