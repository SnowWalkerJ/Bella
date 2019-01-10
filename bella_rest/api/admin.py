from django.contrib import admin

from .models.ctp_account import CTPAccount
from .models.service import Service
from .models.task import Task
# Register your models here.
admin.site.register(CTPAccount)
admin.site.register(Service)
admin.site.register(Task)