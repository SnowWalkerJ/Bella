from mongoengine import Document, ListField, StringField, DecimalField, IntField


class Futures(Document):
    name      = StringField()
    code      = StringField(primary_key=True)
    exchange  = StringField()
    margin    = DecimalField(precision=3)
    rateFee   = DecimalField(precision=5)
    fixFee    = DecimalField(precision=2)
    priceTick = DecimalField(precision=2)
    multiple  = IntField()
    periods   = ListField(ListField(StringField(regex="[0-9]{2}:[0-9]{2}")))
