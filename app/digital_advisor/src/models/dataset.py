from src.extensions import db

class Dataset(db.Model):
    __tablename__ = 'cleaned_dataset'

    company_prefix = db.Column(db.String(10), primary_key=True)
    date_value = db.Column(db.DateTime, primary_key=True)
    open_value = db.Column(db.Float, nullable=False)
    high_value = db.Column(db.Float, nullable=False)
    low_value = db.Column(db.Float, nullable=False)
    close_value = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)

    # Unique constraint to ensure one entry per ticker per day
    __table_args__ = (db.UniqueConstraint('company_prefix', 'date_value', name='_company_date_uc'),)
    
    gdp_growth = db.Column(db.Float, nullable=True)
    consumer_price_index_for_all_urban_consumers = db.Column(db.Float, nullable=True)
    retail_sales_data_excluding_food_services = db.Column(db.Float, nullable=True)
    crude_oil_price = db.Column(db.Float, nullable=True)
    interest_rate_fed_funds = db.Column(db.Float, nullable=True)
    stock_market_volatility_vix_index = db.Column(db.Float, nullable=True)
    ten_year_treasury_yield = db.Column(db.Float, name="10_year_treasury_yield", nullable=True)

    def __repr__(self):
        return f'<Dataset {self.company_prefix} @ {self.date_value}>'
