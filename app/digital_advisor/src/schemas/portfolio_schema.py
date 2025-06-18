from marshmallow import Schema, fields, validate

class PortfolioSchema(Schema):
    portfolio_id = fields.Int(dump_only=True)
    user_id = fields.Int(dump_only=True)
    ticker = fields.Str(required=True, validate=validate.Length(max=8))
    volume = fields.Float(required=True)

class PortfolioTradeSchema(Schema):
    ticker = fields.Str(required=True, validate=validate.Length(max=8))
    volume = fields.Float(required=True, validate=validate.Range(min=0.0001))
