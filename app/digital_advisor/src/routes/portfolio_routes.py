from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from src.services import portfolio_service as ps
from src.services.price_service import get_latest_prices_for_tickers
from src.schemas.portfolio_schema import PortfolioSchema, PortfolioTradeSchema
from src.models.user import User
from src.extensions import db  # Required for rollback on exception

portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

portfolio_schema = PortfolioSchema()
portfolio_list_schema = PortfolioSchema(many=True)
portfolio_trade_schema = PortfolioTradeSchema()

@portfolio_bp.route('', methods=['GET'])
@jwt_required()
def get_portfolio():
    """
    Retrieves the user's current asset holdings (portfolio) and cash balance.
    """
    user_id = int(get_jwt_identity())
    try:
        holdings = ps.get_portfolio_by_user(user_id)
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'msg': 'User not found'}), 404

        result_holdings = portfolio_list_schema.dump(holdings)
        return jsonify(holdings=result_holdings, cash_balance=user.balance), 200
    except Exception as e:
        print(f"Error fetching portfolio for user {user_id}: {e}")
        return jsonify({'msg': 'Failed to retrieve portfolio. Please try again later.'}), 500
    

@portfolio_bp.route('/buy', methods=['POST'])
@jwt_required()
def buy_asset_route():
    """
    Handles buying a specific asset.
    """
    user_id = int(get_jwt_identity())
    json_data = request.get_json() or {}

    try:
        data = portfolio_trade_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    ticker = data['ticker'].upper()
    volume = data['volume']

    prices = get_latest_prices_for_tickers([ticker])
    price_per_unit = prices.get(ticker)
    if price_per_unit is None:
        return jsonify({'msg': f'Price for ticker {ticker} not found.'}), 404

    try:
        portfolio_entry, current_balance = ps.buy_ticker(user_id, ticker, volume, price_per_unit)
        result = portfolio_schema.dump(portfolio_entry)
        return jsonify(message='Buy successful', holding=result, new_balance=current_balance), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error processing buy for user {user_id}, ticker {ticker}: {e}")
        return jsonify({'msg': 'An unexpected error occurred during the buy transaction.'}), 500


@portfolio_bp.route('/sell', methods=['POST'])
@jwt_required()
def sell_asset_route():
    """
    Handles selling a specific asset.
    """
    user_id = int(get_jwt_identity())
    json_data = request.get_json() or {}

    try:
        data = portfolio_trade_schema.load(json_data)
    except ValidationError as err:
        return jsonify({'msg': 'Invalid input', 'errors': err.messages}), 400

    ticker = data['ticker'].upper()
    volume = data['volume']

    prices = get_latest_prices_for_tickers([ticker])
    price_per_unit = prices.get(ticker)
    if price_per_unit is None:
        return jsonify({'msg': f'Price for ticker {ticker} not found.'}), 404

    try:
        portfolio_entry, current_balance = ps.sell_ticker(user_id, ticker, volume, price_per_unit)
        result_holding = portfolio_schema.dump(portfolio_entry) if portfolio_entry else None
        return jsonify(
            message='Sell successful',
            holding=result_holding,
            new_balance=current_balance
        ), 200
    except ValueError as e:
        return jsonify({'msg': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error processing sell for user {user_id}, ticker {ticker}: {e}")
        return jsonify({'msg': 'An unexpected error occurred during the sell transaction.'}), 500