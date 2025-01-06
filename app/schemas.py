from marshmallow import Schema, fields

class BuySellConditionsSchema(Schema):
    """Схема для валидации покупки й продажу."""
    indicator = fields.Str(required=True)
    threshold = fields.Float(required=True)


class StrategySchema(Schema):
    """Схема для валідації торгів."""
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    asset_type = fields.Str(required=True)
    buy_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    sell_conditions = fields.Nested(BuySellConditionsSchema, required=True)
    status = fields.Str(required=True, validate=lambda x: x in ['active', 'inactive'])