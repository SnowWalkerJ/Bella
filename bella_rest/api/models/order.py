from django.db import models


class Order(models.Model):
    ID = models.AutoField(primary_key=True)
    Account = models.ForeignKey("CTPAccount", on_delete=models.CASCADE)
    InstrumentID = models.CharField(max_length=20)
    Direction = models.CharField(max_length=1)
    Offset = models.CharField(max_length=1)
    Price = models.CharField(max_length=8)
    VolumesTotal = models.IntegerField()
    VolumesTraded = models.IntegerField(default=0)
    InsertTime = models.DateTimeField()
    SplitSleepAfterSubmit = models.FloatField()
    SplitSleepAfterCancel = models.FloatField()
    SplitPercent = models.FloatField()
    # CancelTime = models.DateTimeField(null=True)
    CompleteTime = models.DateTimeField(null=True)
    Finished = models.BooleanField(default=False)
