# backend/app/models/prediction.py

from src.extensions import db
from datetime import datetime

class Prediction(db.Model):
    """
    Represents a stored price prediction for a given company.
    The 'timestamp' column indicates the specific time (e.g., minute) for which the price is predicted.
    """
    __tablename__ = 'app_data' # As per your model

    prediction_id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False) # e.g., 'AAPL', 'META'
    
    # This timestamp now represents the specific date/time for which the price is predicted (e.g., T+1 minute)
    timestamp = db.Column(db.DateTime, nullable=False) 
    
    predicted_price = db.Column(db.Float, nullable=False) 

    # --- FIX HERE: Changed 'company_prefix' to 'ticker' in UniqueConstraint ---
    __table_args__ = (db.UniqueConstraint('ticker', 'timestamp', name='_company_predicted_date_uc'),)
    # --- END FIX ---

    def __repr__(self):
        return (f'<Prediction {self.prediction_id}: {self.ticker} '
                f'for {self.timestamp} = {self.predicted_price:.2f}>')

