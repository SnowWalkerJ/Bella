from django.db import models


class CTPOrder(models.Model):
    # Primary Keys
    BrokerID = models.CharField(max_length=20)
    InvestorID = models.CharField(max_length=20)
    OrderRef = models.CharField(max_length=20, primary_key=True)

    # Foreign Key
    OrderID = models.ForeignKey("Order", on_delete=models.CASCADE)

    # Fields
    FrontID = models.CharField(max_length=20)
    InstrumentID = models.CharField(max_length=20)
    Direction = models.CharField(max_length=1)
    Offset = models.CharField(max_length=1)
    Price = models.DecimalField(max_digits=7, decimal_places=2)
    VolumesTotal = models.IntegerField()
    VolumesTraded = models.IntegerField()
    InsertTime = models.DateTimeField()
    UpdateTime = models.DateTimeField(null=True)
    CancelTime = models.DateTimeField(null=True)
    CompleteTime = models.DateTimeField(null=True)
    StatusMsg = models.CharField(blank=True, null=True, max_length=80)
    Finished = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['BrokerID', 'InvestorID', 'OrderRef']),
        ]
        unique_together = (
            ('BrokerID', 'InvestorID', 'OrderRef'),
        )
