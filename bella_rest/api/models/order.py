from django.db import models


class Order(models.Model):
    ID = models.AutoField(primary_key=True)
    InstrumentID = models.CharField(max_length=20)
    Direction = models.CharField(max_length=1)
    Offset = models.CharField(max_length=1)
    Price = models.CharField(max_length=8)
    Volume = models.IntegerField()
    InsertTime = models.DateTimeField(auto_now=True)
