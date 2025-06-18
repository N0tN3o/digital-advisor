from marshmallow import Schema, fields, validates, ValidationError

class DepositWithdrawSchema(Schema):
    amount = fields.Float(required=True)

    @validates('amount')
    def validate_amount(self, value, **kwargs):
        if value <= 0:
            raise ValidationError("Amount must be greater than zero.")