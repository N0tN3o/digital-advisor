# backend/app/schemas/transaction_schema.py

from marshmallow import Schema, fields, validate

class TransactionSchema(Schema):
    """
    Marshmallow schema for serializing and deserializing Transaction objects.
    """
    transaction_id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    # Ticker can be None for cash transactions
    ticker = fields.Str(validate=validate.Length(max=8), allow_none=True, 
                        metadata={"description": "The stock ticker symbol (e.g., AAPL) or null for cash transactions"})
    # Updated validation to include 'deposit' and 'withdraw'
    transaction_type = fields.Str(required=True, validate=validate.OneOf(['BUY', 'SELL', 'DEPOSIT', 'WITHDRAW']), 
                                   metadata={"description": "Type of transaction: 'BUY', 'SELL', 'DEPOSIT', 'WITHDRAW'"})
    volume = fields.Float(required=True, validate=validate.Range(min=0.0001), 
                          metadata={"description": "The number of units traded or the amount for cash transactions"})
    price_per_unit = fields.Float(required=True, validate=validate.Range(min=0.0001), 
                                  metadata={"description": "The price per unit at the time of transaction (1.0 for cash transactions)"})
    total_amount = fields.Float(dump_only=True, 
                                metadata={"description": "The total amount of the transaction (volume * price_per_unit)"})
    timestamp = fields.DateTime(dump_only=True, 
                                metadata={"description": "The UTC timestamp of the transaction"})
