from django.db import models


class CTPOrder(models.Model):
    # Primary Keys
    BrokerID = models.IntegerField()
    InvestorID = models.IntegerField()
    OrderRef = models.IntegerField()

    # Foreign Key
    OrderID = models.ForeignKey("Order", on_delete=models.CASCADE)

    # Fields
    InstrumentID = models.CharField(max_length=20)
    Direction = models.CharField(max_length=1)
    Offset = models.CharField(max_length=1)
    Price = models.DecimalField(max_digits=7, decimal_places=2)
    Volume = models.IntegerField()
    InsertTime = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['BrokerID', 'InvestorID', 'OrderRef']),
        ]
        unique_together = (
            ('BrokerID', 'InvestorID', 'OrderRef'),
        )
