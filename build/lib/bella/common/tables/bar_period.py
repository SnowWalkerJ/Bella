from mongoengine import Document, StringField


class BarPeriod(Document):
    period = StringField(regex="[0-9]{1,2}[smhd]")
