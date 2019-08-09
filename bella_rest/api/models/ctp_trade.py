from django.db import models


class CTPTrade(models.Model):
    # Primary Key
    TradeID = models.CharField(primary_key=True, max_length=20)

    # Foreign Key
    CTPOrderID = models.ForeignKey("CTPOrder", on_delete=models.CASCADE)

    # Original Fields
    Instrument = models.ForeignKey("Instrument", on_delete=models.CASCADE)
    Price = models.DecimalField(max_digits=7, decimal_places=2)
    Volume = models.IntegerField()
    Direction = models.CharField(max_length=1)
    OffsetFlag = models.CharField(max_length=1)

    # Additional Fields
    TradeTime = models.DateTimeField()
