from datetime import datetime
from dateutil.parser import parse

import ujson
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.schemas import AutoSchema
from rest_framework.response import Response
from arctic.date import DateRange
import coreapi
from bella.db import redis

from .models.ctp_account import CTPAccount
from .models.service import Service
from .models.task import Task
from .models.bar_period import BarPeriod
from .models.instrument import Instrument
from .models.order import Order
from .models.ctp_order import CTPOrder
from .models.ctp_trade import CTPTrade
from .serializers import (
    CTPAccountSerializer,
    ServiceSerializer,
    TaskSerializer,
    BarPeriodSerializer,
    InstrumentSerializer,
    OrderSerializer,
    CTPOrderSerializer,
    CTPTradeSerializer,
)


class CTPAccountViewSet(ReadOnlyModelViewSet):
    queryset = CTPAccount.objects.all()
    serializer_class = CTPAccountSerializer


class BarPeriodViewSet(ReadOnlyModelViewSet):
    queryset = BarPeriod.objects.all()
    serializer_class = BarPeriodSerializer


class ServiceViewSet(ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request):
        account = get_object_or_404(CTPAccount.objects.all(), pk=request.data["Account"])
        serializer = self.serializer_class()
        data = {
            "Account": account,
            "InstrumentID": request.data["InstrumentID"],
            "Price": request.data["Price"],
            "VolumesTraded": 0,
            "VolumesTotal": int(request.data["VolumesTotal"]),
            "Direction": request.data["Direction"],
            "Offset": request.data["Offset"],
            "InsertTime": parse(request.data["InsertTime"]),
            "SplitSleepAfterSubmit": float(request.data["SplitSleepAfterSubmit"]),
            "SplitSleepAfterCancel": float(request.data["SplitSleepAfterCancel"]),
            "SplitPercent": float(request.data["SplitPercent"]),
            "Status": 0,
        }
        order = serializer.create(data)
        order.save()
        return Response({"ID": order.ID})


class CTPOrderViewSet(ModelViewSet):
    queryset = CTPOrder.objects.all()
    serializer_class = CTPOrderSerializer

    def partial_update(self, request, pk=None):
        result = super().partial_update(request, id)
        queryset = CTPOrder.objects.all()
        order = get_object_or_404(queryset, pk=pk).OrderID
        related_ctp_orders = CTPOrder.objects.filter(OrderID=order)
        volumes_traded = sum((o.VolumesTraded for o in related_ctp_orders), 0)
        order.VolumesTraded = volumes_traded
        if order.VolumesTraded == order.VolumesTotal and not order.Finished:
            order.Status = 2
            order.CompleteTime = datetime.now()
        order.save()
        return result


class CTPTradeViewSet(ModelViewSet):
    queryset = CTPTrade.objects.all()
    serializer_class = CTPTradeSerializer


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class InstrumentView(APIView):
    schema = AutoSchema([
        coreapi.Field("data", False, "form", description="instrument data"),
    ])

    def get(self, request):
        today = datetime.now().strftime("%Y-%m-%d")
        data = Instrument.objects.filter(ExpireDate__gt=today)
        return Response([x.InstrumentID for x in data])

    def put(self, request):
        data = request.data['data']
        old = list(Instrument.objects.all())
        old_ids = set(x.InstrumentID for x in old)
        serializer = InstrumentSerializer()
        for name, instrument in data.items():
            if name in old_ids:
                continue
            instrument = serializer.create(instrument)
            instrument.save()
        return Response()


class BarDataView(APIView):
    schema = AutoSchema([
        coreapi.Field("contract", True, "form", type="string", description="Contract Id"),
        coreapi.Field("freq", True, "form", type="string", description="Bar Frequency"),
        coreapi.Field("start_dt", False, "form", type="string", description="start datetime"),
        coreapi.Field("end_dt", False, "form", type="string", description="end datetime"),
    ])

    def get(self, request):
        """从arctic数据库中拉取K线数据"""
        contract = request.query_params['contract']
        freq = request.query_params['freq']
        start_dt = request.query_params.get('start_dt')
        end_dt = request.query_params.get('end_dt')

        lib = arctic.get_library(f"bar.{freq}")
        date_range = DateRange(start_dt, end_dt)
        data = lib.read(contract, date_range=date_range)
        return data.to_dict(orient='index')


class QueryOrderFromCTPOrder(APIView):
    def get(self, request, pk):
        queryset = CTPOrder.objects.all()
        ctp_order = get_object_or_404(queryset, pk=pk)
        return Response({"OrderID": ctp_order.OrderID.ID})


class Position(APIView):
    def get(self, request):
        data = {}
        keys = redis.hkeys("Position")
        for key in keys:
            data[key] = ujson.loads(redis.hget("Position", key))
        return Response(data)
