from marshmallow import Schema, fields

class PredictionResponseSchema(Schema):
    predicted_close_value = fields.Float(required=True, allow_none=False)