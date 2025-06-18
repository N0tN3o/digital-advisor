from src.extensions import db

class Portfolio(db.Model):
    __tablename__ = 'user_portfolio'

    portfolio_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    ticker = db.Column(db.String(8), nullable=False)
    volume = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relationship to user
    user = db.relationship('User', back_populates='portfolios', lazy=True)
    
    # Ensure a user has only one entry per ticker in their portfolio
    __table_args__ = (db.UniqueConstraint('user_id', 'ticker', name='_user_ticker_uc'),)

    def __repr__(self):
        return f'<Portfolio {self.portfolio_id}: User {self.user_id} - {self.ticker} ({self.volume})>'