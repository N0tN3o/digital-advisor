# app/services/prediction_service.py

from src.config import (
    MODEL_TYPE1_CONFIG, MODEL_TYPE2_CONFIG,
    COMPANIES_TYPE1, COMPANIES_TYPE2
)
from src.models.dataset import Dataset
from src.extensions import db
from src.utils.prediction_utils import ModelManager, BasePreprocessor, Type2Preprocessor
from src.services.prediction_storage_service import PredictionStorageService 
from typing import List, Dict, Union
import numpy as np
import pandas as pd
from datetime import datetime, timedelta 
import logging

logger = logging.getLogger(__name__)


# --- Core Prediction Service ---
class PredictionService:
    def __init__(self):
        self.predictor = Predictor()
        self.prediction_storage = PredictionStorageService() 

    def run_prediction(self, company: str, features_from_request: dict = None) -> float:
        """
        Prepares input data for the prediction model by fetching historical Datasets,
        deriving technical indicators, and collecting all required features.
        Then, it runs the prediction and saves the result to the database.
        It first checks if a prediction for the target timestamp already exists.

        Parameters:
        - company: The company ticker (e.g., 'AAPL').
        - features_from_request: Optional. If provided, these features are used directly,
                                 bypassing database lookup and feature engineering.
                                 This is useful for direct prediction based on external input.

        Returns:
        - predicted_close_value: The predicted closing Dataset as a float.
        """
        company = company.upper()

        # Determine model type and relevant configs
        model_config = None
        if company in COMPANIES_TYPE1:
            model_config = MODEL_TYPE1_CONFIG
        elif company in COMPANIES_TYPE2:
            model_config = MODEL_TYPE2_CONFIG
        else:
            raise ValueError(f"Company '{company}' is not configured for prediction. "
                             "Please ensure it's in COMPANIES_TYPE1 or COMPANIES_TYPE2.")

        current_seq_length = model_config["SEQ_LENGTH"]
        current_features = model_config["FEATURES"]

        # --- Determine the target timestamp for prediction (T+1 minute) ---
        # This is the timestamp for which we are making/checking the prediction.
        predicted_for_db_timestamp = None
        if features_from_request:
            # If features are provided directly, we assume it's for the next full minute from now.
            predicted_for_db_timestamp = (datetime.utcnow().replace(second=0, microsecond=0) + timedelta(minutes=1))
        else:
            # We need to query for the last available data point to determine the predicted_for_db_timestamp.
            # Query just the date_value for the last minute to find the timestamp.
            last_data_point_query = db.session.query(Dataset.date_value)\
                                          .filter(Dataset.company_prefix == company)\
                                          .order_by(Dataset.date_value.desc())\
                                          .limit(1)\
                                          .first()
            if last_data_point_query:
                last_input_data_timestamp = last_data_point_query.date_value
                predicted_for_db_timestamp = last_input_data_timestamp + timedelta(minutes=1)
            else:
                logger.warning(f"No historical data found for {company} to determine prediction timestamp. Proceeding with current time + 1min as fallback.")
                predicted_for_db_timestamp = (datetime.utcnow().replace(second=0, microsecond=0) + timedelta(minutes=1))

        if not predicted_for_db_timestamp:
            raise RuntimeError(f"Could not determine a valid timestamp for prediction for {company}.")


        # --- NEW: Check for existing prediction in DB first (without nested transaction for read) ---
        try:
            existing_prediction = self.prediction_storage.get_prediction_for_timestamp(
                company_ticker=company, 
                target_timestamp=predicted_for_db_timestamp
            )
            if existing_prediction:
                logger.info(f"Found existing prediction for {company} at {predicted_for_db_timestamp}. Returning cached value.")
                # We don't commit here. The main request's session will handle the commit/rollback.
                return float(existing_prediction.predicted_price)
            else:
                logger.info(f"No existing prediction for {company} at {predicted_for_db_timestamp}. Generating new prediction.")
        except Exception as e:
            # No rollback needed here for a simple read lookup that isn't part of a nested transaction.
            logger.error(f"Error checking for existing prediction for {company} at {predicted_for_db_timestamp}: {e}", exc_info=True)
            # Decide if prediction failure should block the API response:
            # For now, we'll continue to try generating a new one if lookup fails.

        # --- Proceed with prediction if no existing one was found or lookup failed ---
        raw_input_data = {} # Initialize raw_input_data
        if features_from_request:
            raw_input_data = features_from_request
            # Validation for `features_from_request` path already exists above and is fine.
        else:
            # Re-query historical data for prediction generation (might be slightly different if time passed)
            # Fetch full required data points for feature engineering if not from request
            max_rolling_window = 30 
            required_raw_data_points = current_seq_length + max_rolling_window + 5 

            base_query_columns = [
                Dataset.date_value, Dataset.close_value, Dataset.volume,
                Dataset.gdp_growth, Dataset.consumer_price_index_for_all_urban_consumers,
                Dataset.retail_sales_data_excluding_food_services, Dataset.crude_oil_price,
                Dataset.interest_rate_fed_funds, Dataset.stock_market_volatility_vix_index,
                Dataset.ten_year_treasury_yield
            ]

            historical_data_rows = db.session.query(*base_query_columns)\
                                          .filter(Dataset.company_prefix == company)\
                                          .order_by(Dataset.date_value.desc())\
                                          .limit(required_raw_data_points)\
                                          .all()
            historical_data_rows.sort(key=lambda x: x.date_value)

            if len(historical_data_rows) < required_raw_data_points:
                raise ValueError(f"Not enough historical data for {company} after lookup. Need at least {required_raw_data_points} data points (for features and lookback), got {len(historical_data_rows)}.")

            historical_df = pd.DataFrame([row._asdict() for row in historical_data_rows], columns=[col.key for col in base_query_columns])
            historical_df = historical_df.set_index('date_value').sort_index()

            # --- Feature Engineering (Unified Pandas Approach) ---
            historical_df['ma10'] = historical_df['close_value'].rolling(window=10).mean()
            historical_df['ma30'] = historical_df['close_value'].rolling(window=30).mean()
            historical_df['volatility'] = historical_df['close_value'].rolling(window=10).std()

            features_to_dropna_on = [f for f in current_features if f not in ['log_returns']] 
            historical_df = historical_df[current_features].dropna(subset=features_to_dropna_on)

            if len(historical_df) < current_seq_length:
                raise ValueError(f"Not enough clean historical data after feature engineering and dropping NaNs for {company}. "
                                 f"Need {current_seq_length} data points, got {len(historical_df)}.")

            for feature_name in current_features:
                raw_input_data[feature_name] = historical_df[feature_name].iloc[-current_seq_length:].tolist()
            
            for feature in current_features:
                if feature not in raw_input_data or len(raw_input_data[feature]) != current_seq_length:
                    raise ValueError(f"Error preparing input: Feature '{feature}' is missing or has incorrect length "
                                     f"({len(raw_input_data.get(feature, []))}) for SEQ_LENGTH {current_seq_length}.")


        predicted_value = self.predictor.predict(company, raw_input_data)

        # --- Save the newly generated prediction to the database ---
        # predicted_for_db_timestamp is already determined and validated.
        try:
            # Use begin_nested here for the write operation for atomicity
            with db.session.begin_nested(): 
                self.prediction_storage.save_prediction(
                    company_ticker=company, 
                    predicted_for_timestamp=predicted_for_db_timestamp, 
                    predicted_value=predicted_value 
                )
            db.session.commit() # Commit the nested transaction for the save
            logger.info(f"Successfully saved new prediction for {company} for {predicted_for_db_timestamp}.")
        except Exception as e:
            db.session.rollback() # Rollback in case of save error
            logger.error(f"Failed to save newly generated prediction for {company} for {predicted_for_db_timestamp}: {e}", exc_info=True)
            # The API call will still return the predicted_value, but the save operation failed.

        return float(predicted_value)

# --- Predictor Class (Orchestrates Preprocessing and Model Prediction) ---
# This class remains unchanged as it only predicts, not saves.
class Predictor:
    def __init__(self):
        self.model_manager = ModelManager()
        self.preprocessors: Dict[str, Union[BasePreprocessor, Type2Preprocessor]] = {}

    def predict(self, company: str, raw_input_data: Dict[str, List[float]]) -> float:
        model_config = None
        if company in COMPANIES_TYPE1:
            model_config = MODEL_TYPE1_CONFIG
        elif company in COMPANIES_TYPE2:
            model_config = MODEL_TYPE2_CONFIG
        else:
            raise ValueError(f"Company '{company}' not recognized for prediction in any model type. "
                             "This should have been caught earlier.")

        preprocessor_class = BasePreprocessor if company in COMPANIES_TYPE1 else Type2Preprocessor

        if company not in self.preprocessors:
            self.preprocessors[company] = preprocessor_class(company)
        preprocessor = self.preprocessors[company]

        model_input = preprocessor.prepare_input_sequence(raw_input_data)
        model = self.model_manager.get_model(company)
        prediction_scaled = model.predict(model_input)
        predicted_price = preprocessor.inverse_transform_prediction(prediction_scaled)

        return float(predicted_price)
