from django.db import models


class BarPeriod(models.Model):
    period = models.CharField(primary_key=True, max_length=10)
