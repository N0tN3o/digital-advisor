from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.services.price_service import get_latest_prices_for_tickers

price_bp = Blueprint('price', __name__)

@price_bp.route('/prices', methods=['GET'])
def get_latest_prices():
    tickers = request.args.get('tickers')
    if not tickers:
        return jsonify({"msg": "Missing tickers query parameter"}), 400

    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    prices = get_latest_prices_for_tickers(ticker_list)
    return jsonify(prices), 200