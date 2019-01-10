from mongoengine import Document, StringField


class MainContract(Document):
    contract  = StringField()
    symbol    = StringField()
    startDate = StringField()
    endDate   = StringField()
