from src.models.dataset import Dataset
from src.extensions import db
from sqlalchemy import func

def get_latest_prices_for_tickers(tickers):
    """
    Returns a dictionary mapping each ticker to its latest close_value.
    """
    subquery = (
        db.session.query(
            Dataset.company_prefix,
            func.max(Dataset.date_value).label("latest_date")
        )
        .filter(Dataset.company_prefix.in_(tickers))
        .group_by(Dataset.company_prefix)
        .subquery()
    )

    query = (
        db.session.query(Dataset)
        .join(subquery, (Dataset.company_prefix == subquery.c.company_prefix) &
                        (Dataset.date_value == subquery.c.latest_date))
    )

    result = query.all()
    return {row.company_prefix: row.close_value for row in result}
