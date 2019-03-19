from django.db import models


class CTPTrade(models.Model):
    # Primary Key
    TradeID = models.CharField(primary_key=True, max_length=20)

    # Foreign Key
    CTPOrderID = models.ForeignKey("CTPOrder", on_delete=models.CASCADE)

    # Fields
    Price = models.DecimalField(max_digits=7, decimal_places=2)
    Volume = models.IntegerField()
    TradeTime = models.DateTimeField()
