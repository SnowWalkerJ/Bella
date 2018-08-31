from mongoengine import Document, StringField, BooleanField


class Service(Document):
    Name    = StringField(primary_key=True)
    Command = StringField()
    LogFile = StringField()
    Status  = BooleanField(default=False)
