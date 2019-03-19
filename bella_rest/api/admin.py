from django.contrib import admin

from .models.ctp_account import CTPAccount
from .models.service import Service
from .models.task import Task
from .models.order import Order
from .models.ctp_order import CTPOrder
from .models.ctp_trade import CTPTrade
# Register your models here.
admin.site.register(CTPAccount)
admin.site.register(Service)
admin.site.register(Task)
admin.site.register(Order)
admin.site.register(CTPOrder)
admin.site.register(CTPTrade)
