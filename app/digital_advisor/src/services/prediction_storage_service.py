# backend/src/services/prediction_storage_service.py

from src.extensions import db
from src.models.prediction import Prediction 
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PredictionStorageService:
    """
    Service for storing and retrieving predicted stock prices from the database.
    """
    def save_prediction(self, company_ticker: str, predicted_for_timestamp: datetime, predicted_value: float) -> Prediction:
        """
        Saves a single stock price prediction to the database.

        Args:
            company_ticker (str): The ticker symbol of the company.
            predicted_for_timestamp (datetime): The UTC timestamp that this prediction is for (e.g., the next minute).
            predicted_value (float): The predicted closing price.

        Returns:
            Prediction: The newly created or updated Prediction object.
        """
        if not all([company_ticker, predicted_for_timestamp, predicted_value is not None]):
            raise ValueError("All prediction parameters (company_ticker, predicted_for_timestamp, predicted_value) must be provided.")
        
        try:
            # Check if a prediction for this ticker and timestamp already exists
            existing_prediction = Prediction.query.filter_by(
                ticker=company_ticker, 
                timestamp=predicted_for_timestamp
            ).first()

            if existing_prediction:
                return existing_prediction
            else:
                # Create a new prediction entry
                new_prediction = Prediction(
                    ticker=company_ticker, 
                    timestamp=predicted_for_timestamp, 
                    predicted_price=predicted_value 
                )
                db.session.add(new_prediction)
                logger.info(f"Saved new prediction for {company_ticker} for {predicted_for_timestamp}: {predicted_value:.2f}")
                return new_prediction

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving prediction for {company_ticker} for {predicted_for_timestamp}: {e}", exc_info=True)
            raise 

    def get_latest_prediction(self, company_ticker: str) -> Prediction:
        """
        Retrieves the most recent prediction for a given company based on its predicted timestamp.
        """
        return Prediction.query.filter_by(ticker=company_ticker)\
                       .order_by(Prediction.timestamp.desc())\
                       .first()
    
    def get_prediction_for_timestamp(self, company_ticker: str, target_timestamp: datetime) -> Prediction:
        """
        Retrieves a prediction for a specific company and timestamp.
        Returns None if no such prediction exists.
        """
        return Prediction.query.filter_by(
            ticker=company_ticker,
            timestamp=target_timestamp
        ).first()

    def get_predictions_by_company(self, company_ticker: str, limit: int = 10) -> list[Prediction]:
        """
        Retrieves recent predictions for a given company.
        Orders by 'timestamp' descending.
        """
        return Prediction.query.filter_by(ticker=company_ticker)\
                       .order_by(Prediction.timestamp.desc())\
                       .limit(limit)\
                       .all()

