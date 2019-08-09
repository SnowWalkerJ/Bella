from django.db import models


class CTPOrder(models.Model):
    # Primary Keys
    OrderSysID = models.CharField(max_length=20, null=True, blank=True)
    FrontID = models.CharField(max_length=20)
    SessionID = models.CharField(max_length=20)
    OrderRef = models.CharField(max_length=20)

    # Foreign Key
    OrderID = models.ForeignKey("Order", on_delete=models.CASCADE, null=True)

    # Fields
    Account = models.ForeignKey("CTPAccount", on_delete=models.CASCADE)
    InvestorID = models.CharField(max_length=20)
    BrokerID = models.CharField(max_length=20)
    InstrumentID = models.ForeignKey("Instrument", on_delete=models.CASCADE)
    Direction = models.CharField(max_length=1)
    Offset = models.CharField(max_length=1)
    Price = models.DecimalField(max_digits=7, decimal_places=2)
    VolumesTotal = models.IntegerField()
    VolumesTraded = models.IntegerField()
    InsertTime = models.DateTimeField()
    UpdateTime = models.DateTimeField(null=True)
    CancelTime = models.DateTimeField(null=True, blank=True)
    CompleteTime = models.DateTimeField(null=True, blank=True)
    StatusMsg = models.CharField(blank=True, null=True, max_length=80)
    Finished = models.BooleanField(default=False)
    IsDummy = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['FrontID', 'SessionID', 'OrderRef']),
            models.Index(fields=['OrderSysID']),
        ]
        unique_together = (
            ('FrontID', 'SessionID', 'OrderRef'),
        )
