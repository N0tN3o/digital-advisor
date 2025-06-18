import re
from src.extensions import db
from src.models.user import User
from flask_jwt_extended import create_access_token
from sqlalchemy import or_

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

def validate_registration_data(username, email, password):
    if not username or not username.strip():
        return 'Username is required'
    if not email or not EMAIL_REGEX.match(email):
        return 'Valid email is required'
    if not password:
        return 'Password is required'
    if len(password) < 8:
        return 'Password must be at least 8 characters long'
    return None

def register_user(username, email, password):
    # Check if user exists
    if User.query.filter(or_(User.username == username, User.email == email)).first():
        return None, 'User with that username or email already exists'
    
    user = User(username=username.strip(), email=email.strip(), balance=0.0)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None

def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return None, 'Bad username or password'
    token = create_access_token(identity=str(user.user_id))
    return token, None

def get_user_by_id(user_id):
    return db.session.get(User, user_id)