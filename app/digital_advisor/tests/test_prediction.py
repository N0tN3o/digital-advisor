# test_prediction.py

import pytest
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import pandas as pd
import datetime
import os
from marshmallow import ValidationError

# Import modules under test
from src.schemas.prediction_schema import PredictionResponseSchema
from src.services.prediction_service import PredictionService, Predictor
from src.utils.prediction_utils import (
    BasePreprocessor,
    Type2Preprocessor,
    ModelManager,
    _calculate_moving_average,
    _calculate_volatility
)
from src.models.dataset import Dataset # For mocking DB queries
from src.extensions import db # For mocking DB session

# --- Dummy Config for Testing ---
# We'll patch src.config for more control, but define structure here
DUMMY_COMPANIES_TYPE1 = ['AAPL', 'GOOG']
DUMMY_COMPANIES_TYPE2 = ['MSFT', 'AMZN']
DUMMY_SEQ_LENGTH_TYPE1 = 5
DUMMY_FEATURES_TYPE1 = ['close_value', 'volume', 'ma10', 'ma30', 'volatility']
DUMMY_MODEL_DIR_TYPE1 = '/tmp/models_type1'
DUMMY_SCALER_DIR_TYPE1 = '/tmp/scalers_type1'

DUMMY_SEQ_LENGTH_TYPE2 = 10
DUMMY_FEATURES_TYPE2 = ['close_value', 'volume', 'gdp_growth', 'cpi', 'retail_sales', 'oil_price', 'interest_rate', 'vix', 'treasury_yield', 'ma10', 'ma30', 'volatility']
DUMMY_MODEL_DIR_TYPE2 = '/tmp/models_type2'
DUMMY_SCALER_DIR_TYPE2 = '/tmp/scalers_type2'
DUMMY_PCA_DIR_TYPE2 = '/tmp/pca_type2'


# --- Fixture for Mocking tests.test_config (NO src.utils.prediction_utils patches here) ---
@pytest.fixture(autouse=True)
def mock_app_test_config():
    """Patches tests.test_config with dummy values for prediction tests."""
    with (
        patch('tests.test_config.COMPANIES_TYPE1', DUMMY_COMPANIES_TYPE1),
        patch('tests.test_config.COMPANIES_TYPE2', DUMMY_COMPANIES_TYPE2),
        patch('tests.test_config.SEQ_LENGTH_TYPE1', DUMMY_SEQ_LENGTH_TYPE1),
        patch('tests.test_config.FEATURES_TYPE1', DUMMY_FEATURES_TYPE1),
        patch('tests.test_config.MODEL_DIR_TYPE1', DUMMY_MODEL_DIR_TYPE1),
        patch('tests.test_config.SCALER_DIR_TYPE1', DUMMY_SCALER_DIR_TYPE1),
        patch('tests.test_config.SEQ_LENGTH_TYPE2', DUMMY_SEQ_LENGTH_TYPE2),
        patch('tests.test_config.FEATURES_TYPE2', DUMMY_FEATURES_TYPE2),
        patch('tests.test_config.MODEL_DIR_TYPE2', DUMMY_MODEL_DIR_TYPE2),
        patch('tests.test_config.SCALER_DIR_TYPE2', DUMMY_SCALER_DIR_TYPE2),
        patch('tests.test_config.PCA_DIR_TYPE2', DUMMY_PCA_DIR_TYPE2)
    ):
        yield

@pytest.fixture
def mock_prediction_utils_config():
    """Patches src.utils.prediction_utils and src.services.prediction_service CONFIG dictionaries with dummy values."""
    dummy_model_type1_config = {
        "COMPANIES": ["AAPL", "GOOG"],
        "SEQ_LENGTH": 5,
        "FEATURES": ['close_value', 'volume', 'ma10', 'ma30', 'volatility'],
        "MODEL_DIR": "/tmp/models_type1",
        "SCALER_DIR": "/tmp/scalers_type1",
        "PCA_DIR": None
    }

    dummy_model_type2_config = {
        "COMPANIES": ["MSFT", "AMZN"],
        "SEQ_LENGTH": 10,
        "FEATURES": [
            'close_value', 'volume', 'gdp_growth', 'cpi', 'retail_sales',
            'oil_price', 'interest_rate', 'vix', 'treasury_yield',
            'ma10', 'ma30', 'volatility'
        ],
        "MODEL_DIR": "/tmp/models_type2",
        "SCALER_DIR": "/tmp/scalers_type2",
        "PCA_DIR": "/tmp/pca_type2"
    }

    with (
        patch('src.utils.prediction_utils.MODEL_TYPE1_CONFIG', dummy_model_type1_config),
        patch('src.utils.prediction_utils.MODEL_TYPE2_CONFIG', dummy_model_type2_config),
        patch('src.utils.prediction_utils.COMPANIES_TYPE1', dummy_model_type1_config["COMPANIES"]),
        patch('src.utils.prediction_utils.COMPANIES_TYPE2', dummy_model_type2_config["COMPANIES"]),

        patch('src.services.prediction_service.MODEL_TYPE1_CONFIG', dummy_model_type1_config),
        patch('src.services.prediction_service.MODEL_TYPE2_CONFIG', dummy_model_type2_config),
        patch('src.services.prediction_service.COMPANIES_TYPE1', dummy_model_type1_config["COMPANIES"]),
        patch('src.services.prediction_service.COMPANIES_TYPE2', dummy_model_type2_config["COMPANIES"])
    ):
        yield

# Mock classes for ModelManager and Preprocessors
class MockKerasModel:
    def predict(self, x):
        # Returns a scaled prediction, e.g., 0.5
        return np.array([[0.5]])

class MockScaler:
    def transform(self, data):
        # Simple mock scaling: just return data * 2
        return data * 2

    def inverse_transform(self, data):
        # Simple mock inverse scaling: just return data / 2
        return data / 2

class MockPCA:
    def transform(self, data):
        # Simple mock PCA: assume it reduces dimensions, e.g., by taking first half of features
        return data[:, :data.shape[1]//2]


# --- BasePreprocessor Tests ---
# Add mock_prediction_utils_config to the test's arguments
@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_init(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor initialization."""
    preprocessor = BasePreprocessor('AAPL')
    mock_joblib_load.assert_called_once_with(os.path.join(DUMMY_SCALER_DIR_TYPE1, 'AAPL_scaler.pkl'))
    assert preprocessor.company == 'AAPL'
    assert preprocessor.seq_length == DUMMY_SEQ_LENGTH_TYPE1 # Fix typo
    assert preprocessor.features == DUMMY_FEATURES_TYPE1
    assert preprocessor.close_value_idx == DUMMY_FEATURES_TYPE1.index('close_value')

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=False) # Simulate scaler not found
def test_base_preprocessor_init_scaler_not_found(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor raises FileNotFoundError if scaler is missing."""
    with pytest.raises(FileNotFoundError, match="Scaler file not found"):
        BasePreprocessor('AAPL')

@patch('joblib.load')
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_init_close_value_not_in_features(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor raises ValueError if 'close_value' isn't in features."""
    # This patch needs to target src.utils.prediction_utils.FEATURES_TYPE1
    with patch.dict('src.utils.prediction_utils.MODEL_TYPE1_CONFIG', {"FEATURES": ['volume', 'ma10']}, clear=False):
        with pytest.raises(ValueError, match="'close_value' not found in features list"):
            BasePreprocessor('AAPL')


@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_transform(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor transform method."""
    preprocessor = BasePreprocessor('AAPL')
    test_data = np.array([[10.0, 20.0]])
    transformed_data = preprocessor.transform(test_data)
    np.testing.assert_array_equal(transformed_data, test_data * 2)

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_inverse_transform_close_value(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor inverse_transform_close_value method."""
    preprocessor = BasePreprocessor('AAPL')
    scaled_close_value = np.array([[100.0]]) # A single scaled value
    inversed_value = preprocessor.inverse_transform_close_value(scaled_close_value)
    expected_value = 100.0 / 2.0
    np.testing.assert_allclose(inversed_value, [expected_value])


@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_prepare_input_sequence_success(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor prepare_input_sequence with valid input."""
    preprocessor = BasePreprocessor('AAPL')
    raw_data = {feature: [float(i) for i in range(DUMMY_SEQ_LENGTH_TYPE1)] for feature in DUMMY_FEATURES_TYPE1}
    
    model_input = preprocessor.prepare_input_sequence(raw_data)
    
    assert model_input.shape == (1, DUMMY_SEQ_LENGTH_TYPE1, len(DUMMY_FEATURES_TYPE1))
    np.testing.assert_allclose(model_input[0, 0, :], np.array([0.0] * len(DUMMY_FEATURES_TYPE1)) * 2)

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_prepare_input_sequence_invalid_length(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor prepare_input_sequence with incorrect feature length."""
    preprocessor = BasePreprocessor('AAPL')
    raw_data = {feature: [float(i) for i in range(DUMMY_SEQ_LENGTH_TYPE1 - 1)] for feature in DUMMY_FEATURES_TYPE1}
    with pytest.raises(ValueError, match="Feature 'close_value' length"):
        preprocessor.prepare_input_sequence(raw_data)

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_prepare_input_sequence_missing_feature(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor prepare_input_sequence with a missing feature."""
    preprocessor = BasePreprocessor('AAPL')
    raw_data = {feature: [float(i) for i in range(DUMMY_SEQ_LENGTH_TYPE1)] for feature in DUMMY_FEATURES_TYPE1}
    del raw_data['close_value']
    with pytest.raises(ValueError, match="Feature 'close_value' length"):
        preprocessor.prepare_input_sequence(raw_data)

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_base_preprocessor_inverse_transform_prediction(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test BasePreprocessor inverse_transform_prediction."""
    preprocessor = BasePreprocessor('AAPL')
    scaled_prediction = np.array([[0.5]])
    predicted_value = preprocessor.inverse_transform_prediction(scaled_prediction)
    np.testing.assert_allclose(predicted_value, 0.25)


# --- Type2Preprocessor Tests ---
@patch('joblib.load')
@patch('os.path.exists', return_value=True)
def test_type2_preprocessor_init(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test Type2Preprocessor initialization."""
    mock_joblib_load.side_effect = [MockScaler(), MockPCA()]
    preprocessor = Type2Preprocessor('MSFT')
    
    mock_joblib_load.assert_any_call(os.path.join(DUMMY_SCALER_DIR_TYPE2, 'MSFT_scaler.pkl'))
    mock_joblib_load.assert_any_call(os.path.join(DUMMY_PCA_DIR_TYPE2, 'MSFT_pca.pkl'))
    
    assert preprocessor.company == 'MSFT'
    assert preprocessor.seq_length == DUMMY_SEQ_LENGTH_TYPE2
    assert preprocessor.features == DUMMY_FEATURES_TYPE2
    assert preprocessor.close_value_idx == DUMMY_FEATURES_TYPE2.index('close_value')

@patch('joblib.load', side_effect=[MockScaler(), FileNotFoundError])
@patch('os.path.exists', side_effect=[True, False])
def test_type2_preprocessor_init_pca_not_found(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test Type2Preprocessor raises FileNotFoundError if PCA is missing."""
    with pytest.raises(FileNotFoundError, match="PCA object not found"):
        Type2Preprocessor('MSFT')

@patch('joblib.load', return_value=MockScaler())
@patch('os.path.exists', return_value=True)
def test_type2_preprocessor_prepare_input_sequence_success(mock_exists, mock_joblib_load, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test Type2Preprocessor prepare_input_sequence with valid input."""
    mock_joblib_load.side_effect = [MockScaler(), MockPCA()]
    preprocessor = Type2Preprocessor('MSFT')

    raw_data = {feature: [float(i) + f_idx * 100 for i in range(DUMMY_SEQ_LENGTH_TYPE2)]
                for f_idx, feature in enumerate(DUMMY_FEATURES_TYPE2)}
    
    model_input = preprocessor.prepare_input_sequence(raw_data)
    
    expected_num_pca_components = len(DUMMY_FEATURES_TYPE2) // 2
    assert model_input.shape == (1, DUMMY_SEQ_LENGTH_TYPE2, expected_num_pca_components)
    
    original_data_2d = np.array([raw_data[feature] for feature in DUMMY_FEATURES_TYPE2]).T
    scaled_data = original_data_2d * 2
    pca_transformed_data = scaled_data[:, :expected_num_pca_components]
    
    np.testing.assert_allclose(model_input[0, :, :], pca_transformed_data)


# --- ModelManager Tests ---
# IMPORTANT: Patch src.utils.prediction_utils.load_model instead of tensorflow.keras.models.load_model
@patch('src.utils.prediction_utils.load_model', return_value=MockKerasModel())
@patch('os.path.exists', return_value=True)
def test_model_manager_get_model_success_type1(mock_exists, mock_load_model, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test ModelManager loads and caches a Type 1 model successfully."""
    manager = ModelManager()
    model = manager.get_model('AAPL')
    # The assert_called_once_with should still use os.path.join with the DUMMY path
    mock_load_model.assert_called_once_with(os.path.join(DUMMY_MODEL_DIR_TYPE1, 'AAPL_model.keras'))
    assert isinstance(model, MockKerasModel)
    assert 'AAPL' in manager.models

    mock_load_model.reset_mock()
    model_cached = manager.get_model('AAPL')
    mock_load_model.assert_not_called()
    assert model_cached == model

@patch('src.utils.prediction_utils.load_model', return_value=MockKerasModel())
@patch('os.path.exists', return_value=True)
def test_model_manager_get_model_success_type2(mock_exists, mock_load_model, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test ModelManager loads and caches a Type 2 model successfully."""
    manager = ModelManager()
    model = manager.get_model('MSFT')
    mock_load_model.assert_called_once_with(os.path.join(DUMMY_MODEL_DIR_TYPE2, 'MSFT_model.keras'))
    assert isinstance(model, MockKerasModel)
    assert 'MSFT' in manager.models

@patch('os.path.exists', return_value=False)
@patch('src.utils.prediction_utils.load_model') # IMPORTANT: Patch src.utils.prediction_utils.load_model
def test_model_manager_get_model_not_found(mock_load_model, mock_exists, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test ModelManager raises FileNotFoundError if model is missing."""
    manager = ModelManager()
    with pytest.raises(FileNotFoundError, match="Model file not found"):
        manager.get_model('AAPL')
    mock_load_model.assert_not_called()

@patch('os.path.exists', return_value=True)
@patch('src.utils.prediction_utils.load_model', side_effect=Exception("Corrupted model file")) # IMPORTANT: Patch src.utils.prediction_utils.load_model
def test_model_manager_get_model_load_failure(mock_load_model, mock_exists, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test ModelManager raises RuntimeError if model loading fails."""
    manager = ModelManager()
    with pytest.raises(RuntimeError, match="Failed to load model"):
        manager.get_model('AAPL')

# Note: test_model_manager_get_model_untest_configured_company does not need the prediction_utils config patch
# because it doesn't involve file paths.
def test_model_manager_get_model_untest_configured_company():
    """Test ModelManager raises ValueError for untest_configured company."""
    manager = ModelManager()
    with pytest.raises(ValueError, match="Company 'XYZ' is not configured for prediction."): # Updated error message to match ModelManager
        manager.get_model('XYZ')

# --- Test Section 3: Prediction Service Tests (from src.services.prediction_service) ---
# Most tests here will need mock_prediction_utils_config
@pytest.fixture
def mock_predictor_and_preprocessors():
    """Mocks Predictor and Preprocessor instances within PredictionService."""
    with patch('src.services.prediction_service.Predictor') as MockPredictorClass, \
         patch('src.utils.prediction_utils.BasePreprocessor') as MockBasePreprocessorClass, \
         patch('src.utils.prediction_utils.Type2Preprocessor') as MockType2PreprocessorClass:
        
        mock_predictor_instance = MockPredictorClass.return_value
        mock_predictor_instance.predict.return_value = 160.0

        mock_base_preprocessor_instance = MockBasePreprocessorClass.return_value
        mock_type2_preprocessor_instance = MockType2PreprocessorClass.return_value

        yield mock_predictor_instance, mock_base_preprocessor_instance, mock_type2_preprocessor_instance


# --- Fixture to patch db.session.query for prediction_service ---
@pytest.fixture
def mock_dataset_query():
    """Mocks db.session.query chain for PredictionService."""
    with patch('src.services.prediction_service.db.session.query') as mock_query:
        # Mocking the chain: query().filter_by().order_by().limit().all()
        mock_all_result = MagicMock() # This will be the result of .all()
        
        mock_limit = MagicMock()
        mock_limit.all.return_value = mock_all_result
        
        mock_order_by = MagicMock()
        mock_order_by.limit.return_value = mock_limit
        
        mock_filter_by = MagicMock()
        mock_filter_by.order_by.return_value = mock_order_by
        
        mock_query_instance = MagicMock()
        mock_query_instance.filter_by.return_value = mock_filter_by # This is the key change for filter_by
        
        mock_query.return_value = mock_query_instance

        # Generate dummy data
        def make_mock_data(seq_len, offset):
            data = []
            for i in range(seq_len):
                row = MagicMock()
                row.date_value = datetime.date(2023, 1, 1) + datetime.timedelta(days=i)
                row.close_value = offset + i
                row.volume = 1000 + i
                row.gdp_growth = 0.02
                row.consumer_price_index_for_all_urban_consumers = 2.5
                row.retail_sales_data_excluding_food_services = 500.0
                row.crude_oil_price = 80.0
                row.interest_rate_fed_funds = 0.05
                row.stock_market_volatility_vix_index = 20.0
                row.ten_year_treasury_yield = 0.03
                row._asdict.return_value = {
                'date_value': row.date_value,
                'close_value': row.close_value,
                'volume': row.volume,
                'gdp_growth': row.gdp_growth,
                'consumer_price_index_for_all_urban_consumers': row.consumer_price_index_for_all_urban_consumers,
                'retail_sales_data_excluding_food_services': row.retail_sales_data_excluding_food_services,
                'crude_oil_price': row.crude_oil_price,
                'interest_rate_fed_funds': row.interest_rate_fed_funds,
                'stock_market_volatility_vix_index': row.stock_market_volatility_vix_index,
                'ten_year_treasury_yield': row.ten_year_treasury_yield
            }
                data.append(row)
            return data

        data_type1 = make_mock_data(DUMMY_SEQ_LENGTH_TYPE1 + max(10, 30, 20) + 5, 100)
        data_type2 = make_mock_data(DUMMY_SEQ_LENGTH_TYPE2 + max(10, 30, 10) + 5, 200)

        # Set the side effect on mock_filter_by to differentiate by `company_prefix`
        def filter_by_side_effect(*args, **kwargs):
            if 'company_prefix' in kwargs:
                company = kwargs['company_prefix']
                if company == 'AAPL':
                    mock_all_result.all.return_value = data_type1
                elif company == 'MSFT':
                    mock_all_result.all.return_value = data_type2
                else:
                    mock_all_result.all.return_value = []
            return mock_filter_by # Return the mock_filter_by object for chaining

        mock_filter_by.side_effect = filter_by_side_effect
        
        yield mock_query_instance # Yield the instance that has filter_by

def test_run_prediction_with_features_from_request(mock_predictor_and_preprocessors, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test run_prediction when features are provided directly."""
    mock_predictor, _, _ = mock_predictor_and_preprocessors
    service = PredictionService()
    
    features = {'close_value': [100, 101, 102], 'volume': [1000, 1010, 1020]}
    
    predicted_value = service.run_prediction('AAPL', features_from_request=features)
    
    assert predicted_value == 160.0
    mock_predictor.predict.assert_called_once_with('AAPL', features)

def test_run_prediction_untest_configured_company():
    """Test run_prediction raises ValueError for untest_configured company."""
    service = PredictionService()
    with pytest.raises(ValueError, match="Company 'XYZ' is not configured for prediction."): # Updated error message
        service.run_prediction('XYZ')

@patch('src.models.dataset.Dataset.query')
def test_run_prediction_not_enough_historical_data(mock_query, app, mock_prediction_utils_config, caplog):
    """Test run_prediction logs warning if not enough historical data."""
    mock_filter_by = MagicMock()
    mock_order_by = MagicMock()
    mock_limit = MagicMock()
    mock_limit.all.return_value = []  # Simulate no data

    mock_order_by.limit.return_value = mock_limit
    mock_filter_by.order_by.return_value = mock_order_by
    mock_query.filter_by.return_value = mock_filter_by
    mock_query.return_value = mock_query

    service = PredictionService()
    with app.app_context(), caplog.at_level("WARNING"):
        service.run_prediction('AAPL')

    assert "No historical data found for AAPL" in caplog.text


# --- Predictor Tests ---
@patch('src.services.prediction_service.ModelManager')
@patch('src.services.prediction_service.BasePreprocessor')
@patch('src.services.prediction_service.Type2Preprocessor')
def test_predictor_predict_success_type1(MockType2Preprocessor, MockBasePreprocessor, MockModelManager, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test Predictor.predict for a Type 1 company."""
    mock_model_manager_instance = MockModelManager.return_value
    mock_keras_model = MagicMock(spec=MockKerasModel)
    mock_keras_model.predict.return_value = np.array([[0.5]])
    mock_model_manager_instance.get_model.return_value = mock_keras_model

    mock_base_preprocessor_instance = MockBasePreprocessor.return_value
    mock_base_preprocessor_instance.prepare_input_sequence.return_value = np.array([[[1.0]]])
    mock_base_preprocessor_instance.inverse_transform_prediction.return_value = 150.0

    predictor = Predictor()
    company = 'AAPL'
    raw_input_data = {'close_value': [100, 101, 102], 'volume': [1000, 1010, 1020]}
    
    predicted_value = predictor.predict(company, raw_input_data)
    
    assert predicted_value == 150.0
    MockBasePreprocessor.assert_called_once_with(company)
    mock_base_preprocessor_instance.prepare_input_sequence.assert_called_once_with(raw_input_data)
    mock_model_manager_instance.get_model.assert_called_once_with(company)
    mock_keras_model.predict.assert_called_once_with(mock_base_preprocessor_instance.prepare_input_sequence.return_value)
    mock_base_preprocessor_instance.inverse_transform_prediction.assert_called_once_with(mock_keras_model.predict.return_value)

@patch('src.services.prediction_service.ModelManager')
@patch('src.services.prediction_service.BasePreprocessor')
@patch('src.services.prediction_service.Type2Preprocessor')
def test_predictor_predict_success_type2(MockType2Preprocessor, MockBasePreprocessor, MockModelManager, mock_prediction_utils_config): # ADD THIS ARGUMENT
    """Test Predictor.predict for a Type 2 company."""
    mock_model_manager_instance = MockModelManager.return_value
    mock_keras_model = MagicMock(spec=MockKerasModel)
    mock_keras_model.predict.return_value = np.array([[0.6]])
    mock_model_manager_instance.get_model.return_value = mock_keras_model

    mock_type2_preprocessor_instance = MockType2Preprocessor.return_value
    mock_type2_preprocessor_instance.prepare_input_sequence.return_value = np.array([[[2.0]]])
    mock_type2_preprocessor_instance.inverse_transform_prediction.return_value = 250.0

    predictor = Predictor()
    company = 'MSFT'
    raw_input_data = {'close_value': [200, 201, 202]}
    
    predicted_value = predictor.predict(company, raw_input_data)
    
    assert predicted_value == 250.0
    MockType2Preprocessor.assert_called_once_with(company)
    mock_type2_preprocessor_instance.prepare_input_sequence.assert_called_once_with(raw_input_data)
    mock_model_manager_instance.get_model.assert_called_once_with(company)
    mock_keras_model.predict.assert_called_once_with(mock_type2_preprocessor_instance.prepare_input_sequence.return_value)
    mock_type2_preprocessor_instance.inverse_transform_prediction.assert_called_once_with(mock_keras_model.predict.return_value)


def test_predictor_predict_unrecognized_company():
    """Test Predictor.predict raises ValueError for unrecognized company."""
    predictor = Predictor()
    with pytest.raises(ValueError, match="Company 'XYZ' not recognized for prediction"):
        predictor.predict('XYZ', {})

# --- Test Section 4: Flask Route Tests (from prediction_routes.py) ---
# These tests typically do not need mock_prediction_utils_config as they mock the service layer.
@pytest.fixture
def mock_prediction_service():
    """Mocks the PredictionService instance used by the Flask blueprint."""
    with patch('src.routes.prediction_routes.PredictionService') as MockServiceClass:
        mock_service_instance = MockServiceClass.return_value
        mock_service_instance.run_prediction.return_value = 165.75
        yield mock_service_instance

@pytest.fixture
def mock_prediction_response_schema():
    """Mocks the PredictionResponseSchema instance used by the Flask blueprint."""
    with patch('src.routes.prediction_routes.PredictionResponseSchema') as MockSchemaClass:
        mock_schema_instance = MockSchemaClass.return_value
        mock_schema_instance.dump.return_value = {"predicted_close_value": 165.75}
        yield mock_schema_instance