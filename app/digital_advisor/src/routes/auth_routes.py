from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from src.services.auth_service import (
    validate_registration_data, register_user, authenticate_user, get_user_by_id
)
from src.schemas.user_schema import UserSchema, UserRegisterSchema, UserLoginSchema

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
user_schema = UserSchema()
register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()

@auth_bp.route('/register', methods=['POST'])
def register():
    json_data = request.get_json() or {}
    try:
        data = register_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    error = validate_registration_data(data['username'], data['email'], data['password'])
    if error:
        return jsonify({'msg': error}), 400

    user, err_msg = register_user(data['username'], data['email'], data['password'])
    if err_msg:
        return jsonify({'msg': err_msg}), 409

    return jsonify({'msg': 'User registered successfully'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    json_data = request.get_json() or {}
    try:
        data = login_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    token, err_msg = authenticate_user(data['username'], data['password'])
    if err_msg:
        return jsonify({'msg': err_msg}), 401

    return jsonify(access_token=token), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404

    return jsonify(user_schema.dump(user)), 200