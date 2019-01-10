from django.db import models


class Task(models.Model):
    Name      = models.CharField(primary_key=True, max_length=100)
    Command   = models.CharField(max_length=100)
    LogFile   = models.CharField(max_length=100)
    Crontab   = models.CharField(max_length=100)
    Activated = models.BooleanField()
