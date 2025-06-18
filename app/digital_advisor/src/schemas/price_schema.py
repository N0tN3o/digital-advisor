from marshmallow import Schema, fields

class PriceSchema(Schema):
    company_prefix = fields.Str(required=True)
    date_value = fields.DateTime(required=True)
    close_value = fields.Float(required=True)