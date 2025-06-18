# app/utils/prediction_utils.py

from src.config import (
    MODEL_TYPE1_CONFIG, MODEL_TYPE2_CONFIG,
    COMPANIES_TYPE1, COMPANIES_TYPE2
)
import numpy as np
import os
import joblib
from typing import List, Dict, Union
from tensorflow.keras.models import load_model

# --- Feature Engineering Functions ---
# These functions are retained as they were in your previously working code,
# but will *not* be used directly for feature engineering in PredictionService.
# They are kept here in case they are used elsewhere or for legacy reasons.
def _calculate_moving_average(data: list[float], window: int) -> list[float]:
    """
    Calculates a simple moving average for a list of data points.
    Returns a list of MA values, padded with initial zeros if data length < window.
    """
    if not data:
        return []
    ma_values = []
    padded_data = [np.nan] * (window - 1) + data
    for i in range(len(data)):
        current_window = padded_data[i : i + window]
        if not any(np.isnan(x) for x in current_window):
            ma_values.append(np.mean(current_window))
        else:
            ma_values.append(0.0)
    return ma_values

def _calculate_volatility(data: list[float], window: int = 20) -> list[float]:
    """
    Calculates historical volatility (standard deviation of log returns).
    Returns a list of volatility values, padded with initial zeros.
    """
    if len(data) < 2:
        return [0.0] * len(data)
    returns = np.diff(np.log(data))
    padded_returns = [0.0] * (window - 1) + returns.tolist()
    volatility_values = []
    for i in range(len(returns)):
        current_window = padded_returns[i : i + window]
        if len(current_window) == window:
            volatility_values.append(np.std(current_window))
        else:
            volatility_values.append(0.0)
    final_volatility = [0.0] * (len(data) - len(volatility_values)) + volatility_values
    return final_volatility

# --- Base Preprocessor Class (for Type 1 Models) ---
class BasePreprocessor:
    """
    Handles preprocessing (scaling, sequence preparation, inverse transformation)
    for models that do not use PCA (i.e., Type 1 models).
    """
    def __init__(self, company: str):
        self.company = company
        self.seq_length = MODEL_TYPE1_CONFIG["SEQ_LENGTH"]
        self.features = MODEL_TYPE1_CONFIG["FEATURES"]

        scaler_path = os.path.join(MODEL_TYPE1_CONFIG["SCALER_DIR"], f"{company}_scaler.pkl")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler file not found for company '{company}' at {scaler_path}")
        self.scaler = joblib.load(scaler_path)

        # Determine the index of 'close_value' in the features list for inverse transformation
        try:
            self.close_value_idx = self.features.index('close_value')
        except ValueError:
            raise ValueError(f"'close_value' not found in features list for {company} (Type 1).")

    def transform(self, data: np.ndarray) -> np.ndarray:
        """Scale data using the loaded scaler."""
        return self.scaler.transform(data)

    def inverse_transform_close_value(self, scaled_data: np.ndarray) -> np.ndarray:
        """
        Inverse transform only the 'close_value' feature from scaled data.
        Assumes scaled_data shape: (num_samples, 1) or (num_samples,)
        """
        # Create a dummy array with the correct number of original features
        dummy = np.zeros((scaled_data.shape[0], len(self.features)))
        # Place the scaled close_value into its correct position
        dummy[:, self.close_value_idx] = scaled_data.ravel()
        # Inverse transform the dummy array
        inversed = self.scaler.inverse_transform(dummy)
        # Return only the inverse-transformed close_value
        return inversed[:, self.close_value_idx]

    def prepare_input_sequence(self, raw_input_data: Dict[str, List[float]]) -> np.ndarray:
        """
        Converts raw input features (dict) into a scaled 3D numpy array
        ready for model input: shape (1, SEQ_LENGTH, num_features).

        Assumes raw_input_data contains a list or array for each feature of length SEQ_LENGTH.
        """
        # Validate that all features have the expected sequence length
        for feature in self.features:
            if feature not in raw_input_data or len(raw_input_data[feature]) != self.seq_length:
                raise ValueError(
                    f"Feature '{feature}' length {len(raw_input_data.get(feature, []))} "
                    f"does not match SEQ_LENGTH {self.seq_length} for company {self.company} (Type 1)."
                )

        # Stack features into a 2D array (SEQ_LENGTH, num_features)
        data = np.array([raw_input_data[feature] for feature in self.features]).T

        # Scale the data
        scaled = self.transform(data)

        # Reshape for model input (1, SEQ_LENGTH, num_features)
        return scaled[np.newaxis, :, :]

    def inverse_transform_prediction(self, scaled_pred: np.ndarray) -> float:
        """
        Given the scaled predicted close_value(s), inverse transform to original scale.
        scaled_pred shape expected to be (1, 1) or (1,).
        """
        scaled_array = scaled_pred.reshape(-1, 1) # Ensure it's 2D for inverse_transform_close_value
        original_values = self.inverse_transform_close_value(scaled_array)
        return float(original_values[0])


# --- Preprocessor Class for Type 2 Models (with PCA) ---
class Type2Preprocessor(BasePreprocessor): # Inherit BasePreprocessor for common methods
    """
    Handles preprocessing for models that use PCA after initial scaling.
    This includes loading the PCA object and performing PCA transform.
    Crucially, it also handles inverse transformation of the *full PCA vector prediction*
    back to original features, then extracts the close_value.
    """
    def __init__(self, company: str):
        self.company = company
        self.seq_length = MODEL_TYPE2_CONFIG["SEQ_LENGTH"]
        self.features = MODEL_TYPE2_CONFIG["FEATURES"] # Use Type 2 specific features

        # Load MinMaxScaler (fitted before PCA)
        scaler_path = os.path.join(MODEL_TYPE2_CONFIG["SCALER_DIR"], f"{company}_scaler.pkl")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler file not found for company '{company}' at {scaler_path}")
        self.scaler = joblib.load(scaler_path)

        # Load PCA object
        pca_path = os.path.join(MODEL_TYPE2_CONFIG["PCA_DIR"], f"{company}_pca.pkl")
        if not os.path.exists(pca_path):
            raise FileNotFoundError(f"PCA object not found for company '{company}' at {pca_path}. "
                                    f"Ensure it was saved during training!")
        self.pca = joblib.load(pca_path)

        # Determine the index of 'close_value' in the features list for inverse transformation
        try:
            self.close_value_idx = self.features.index('close_value')
        except ValueError:
            raise ValueError(f"'close_value' not found in features list for {company} (Type 2).")

    def prepare_input_sequence(self, raw_input_data: Dict[str, List[float]]) -> np.ndarray:
        """
        Converts raw input features (dict) into a scaled, PCA-transformed 3D numpy array
        ready for model input: shape (1, SEQ_LENGTH_TYPE2, num_pca_components).

        Assumes raw_input_data contains a list or array for each feature of length SEQ_LENGTH_TYPE2.
        """
        # Validate that all features have the expected sequence length
        for feature in self.features:
            if feature not in raw_input_data or len(raw_input_data[feature]) != self.seq_length:
                raise ValueError(
                    f"Feature '{feature}' length {len(raw_input_data.get(feature, []))} "
                    f"does not match SEQ_LENGTH {self.seq_length} for company {self.company} (Type 2)."
                )

        # Stack features into a 2D array (SEQ_LENGTH_TYPE2, num_features)
        data = np.array([raw_input_data[feature] for feature in self.features]).T

        # Step 1: Scale the data using MinMaxScaler
        scaled = self.scaler.transform(data)

        # Step 2: Apply PCA transformation
        pca_transformed = self.pca.transform(scaled)

        # Reshape for model input (1, SEQ_LENGTH_TYPE2, num_pca_components)
        return pca_transformed[np.newaxis, :, :]

    def inverse_transform_prediction(self, predicted_pca_vector: np.ndarray) -> float:
        """
        Given the predicted PCA vector (from the model), inverse transform it
        back to the original feature space and then extract the close_value.

        predicted_pca_vector shape expected to be (1, num_pca_components).
        """
        # Step 1: Inverse transform from PCA space back to scaled feature space
        # Expected shape of predicted_pca_vector: (1, num_pca_components)
        reconstructed_scaled = self.pca.inverse_transform(predicted_pca_vector)

        # Step 2: Inverse transform from scaled feature space back to original feature space
        # reconstructed_scaled shape: (1, num_original_features)
        reconstructed_original = self.scaler.inverse_transform(reconstructed_scaled)

        # Step 3: Extract the close_value from the reconstructed original features
        predicted_close_value = reconstructed_original[0, self.close_value_idx]

        return float(predicted_close_value)


# --- Model Manager Class (handles loading models for both types) ---
class ModelManager:
    """
    Loads and caches models for each company, handling different model directories.
    """
    def __init__(self):
        self.models = {}

    def get_model(self, company: str):
        """
        Returns the model instance for the given company.
        Loads it from disk if not already cached.
        """
        if company not in COMPANIES_TYPE1 and company not in COMPANIES_TYPE2:
            raise ValueError(f"Company '{company}' is not configured for prediction.")

        if company not in self.models:
            model_path = None
            if company in COMPANIES_TYPE1:
                model_path = os.path.join(MODEL_TYPE1_CONFIG["MODEL_DIR"], f"{company}_model.keras")
            elif company in COMPANIES_TYPE2:
                # Assuming saved_models_pca is the correct directory for Type 2 models
                model_path = os.path.join(MODEL_TYPE2_CONFIG["MODEL_DIR"], f"{company}_model.keras")

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found for company '{company}' at {model_path}")

            try:
                self.models[company] = load_model(model_path)
            except Exception as e:
                raise RuntimeError(f"Failed to load model from {model_path}: {e}")
        return self.models[company]

