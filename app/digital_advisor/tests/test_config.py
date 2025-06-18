# A simplified app/config.py for testing context
COMPANIES_TYPE1 = ['AAPL', 'GOOG']
COMPANIES_TYPE2 = ['MSFT', 'AMZN']

SEQ_LENGTH_TYPE1 = 5
FEATURES_TYPE1 = ['close_value', 'volume', 'ma10', 'ma30', 'volatility'] # Example subset
MODEL_DIR_TYPE1 = '/tmp/models_type1'
SCALER_DIR_TYPE1 = '/tmp/scalers_type1'

SEQ_LENGTH_TYPE2 = 10
FEATURES_TYPE2 = ['close_value', 'volume', 'gdp_growth', 'consumer_price_index_for_all_urban_consumers', 'retail_sales_data_excluding_food_services', 'crude_oil_price', 'interest_rate_fed_funds', 'stock_market_volatility_vix_index', 'ten_year_treasury_yield', 'ma10', 'ma30', 'volatility'] # Example subset
MODEL_DIR_TYPE2 = '/tmp/models_type2'
SCALER_DIR_TYPE2 = '/tmp/scalers_type2'
PCA_DIR_TYPE2 = '/tmp/pca_type2'