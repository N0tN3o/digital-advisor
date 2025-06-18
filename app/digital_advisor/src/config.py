# app/config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret keys for Flask and JWT (use strong secrets in production)
    SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_default_jwt_secret")

    # Database URI (PostgreSQL recommended for production, fallback to local SQLite)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Base directory for saved artifacts (models, scalers, PCA objects)
BASE_SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'saved_artifacts')) # Assumes saved_artifacts is sibling to app

# --- Consolidated Configuration for Model Types ---

# Configuration for Model Type 1 (APP, PEP, TSLA)
MODEL_TYPE1_CONFIG = {
    "COMPANIES": ["APP", "PEP", "TSLA"],
    "SEQ_LENGTH": 30,
    "FEATURES": [
        'close_value',
        'volume',
        'ma10',
        'ma30',
        'volatility',
        'gdp_growth',
        'consumer_price_index_for_all_urban_consumers',
        'retail_sales_data_excluding_food_services',
        'crude_oil_price',
        'interest_rate_fed_funds',
        'stock_market_volatility_vix_index',
        'ten_year_treasury_yield'
    ],
    "MODEL_DIR": os.path.join(BASE_SAVE_DIR, "saved_models_type1"),
    "SCALER_DIR": os.path.join(BASE_SAVE_DIR, "saved_scalers_type1"),
    "PCA_DIR": None # Type 1 models do not use PCA
}

# Configuration for Model Type 2 (BKNG, META, NVDA, PLTR)
MODEL_TYPE2_CONFIG = {
    "COMPANIES": ["BKNG", "META", "NVDA", "PLTR"],
    "SEQ_LENGTH": 30, # Must match the sequence length used during training for Type 2
    "FEATURES": [
        'close_value',
        'volume',
        'ma10',
        'ma30',
        'volatility',
        'gdp_growth',
        'consumer_price_index_for_all_urban_consumers',
        'retail_sales_data_excluding_food_services',
        'crude_oil_price',
        'interest_rate_fed_funds',
        'stock_market_volatility_vix_index',
        'ten_year_treasury_yield'
    ],
    "MODEL_DIR": os.path.join(BASE_SAVE_DIR, "saved_models_type2"),
    "SCALER_DIR": os.path.join(BASE_SAVE_DIR, "saved_scalers_type2"),
    "PCA_DIR": os.path.join(BASE_SAVE_DIR, "saved_pca_models") # Directory for PCA objects
}

# For convenience, expose the company lists directly as well (for quick checks in other files)
COMPANIES_TYPE1 = MODEL_TYPE1_CONFIG["COMPANIES"]
COMPANIES_TYPE2 = MODEL_TYPE2_CONFIG["COMPANIES"]

# Create directories if they don't exist
os.makedirs(MODEL_TYPE1_CONFIG["MODEL_DIR"], exist_ok=True)
os.makedirs(MODEL_TYPE1_CONFIG["SCALER_DIR"], exist_ok=True)
os.makedirs(MODEL_TYPE2_CONFIG["MODEL_DIR"], exist_ok=True)
os.makedirs(MODEL_TYPE2_CONFIG["SCALER_DIR"], exist_ok=True)
os.makedirs(MODEL_TYPE2_CONFIG["PCA_DIR"], exist_ok=True)