from mongoengine import Document, StringField, BooleanField


class Task(Document):
    Name      = StringField(primary_key=True)
    Command   = StringField()
    LogFile   = StringField()
    Crontab   = StringField()
    Activated = BooleanField()
