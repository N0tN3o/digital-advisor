from flask import Blueprint, request, jsonify
from src.schemas.prediction_schema import PredictionResponseSchema
from src.services.prediction_service import PredictionService

# --- Flask Blueprint and Routes ---
prediction_bp = Blueprint('prediction', __name__, url_prefix='/predict')

response_schema = PredictionResponseSchema()
prediction_service_instance = PredictionService()  # Initialize the service

@prediction_bp.route('', methods=['GET'])
def predict():
    try:
        # Extract the ticker from the query string
        company = request.args.get('ticker')
        if not company:
            return jsonify({"error": "Missing required query parameter: 'ticker'"}), 400

        # No features_from_request passed — will default to internal feature engineering
        predicted_value = prediction_service_instance.run_prediction(company)

        result = {"predicted_close_value": predicted_value}
        return response_schema.dump(result), 200

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Internal server error: {e}")  # For debugging/logging
        return jsonify({"error": "Internal server error"}), 500

