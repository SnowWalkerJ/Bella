from datetime import datetime
from dateutil.parser import parse
import os

import ujson
from django.shortcuts import get_object_or_404
from rest_framework.generics import CreateAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet, GenericViewSet
from rest_framework.views import APIView
from rest_framework.schemas import AutoSchema, ManualSchema
from rest_framework.response import Response
from rest_framework import mixins
from arctic.date import DateRange
import coreapi
from bella.db import redis, arctic as ac
from bella.config import CONFIG

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

    def get_queryset(self):
        qs = self.queryset
        qp = self.request.query_params
        if "Status" in qp:
            qs = qs.filter(Status=qp['Status'])
        if "Account" in qp:
            qs = qs.filter(Account=qp["Account"])
        if "Finished" in qp:
            print(qp['Finished'])
            if qp['Finished']:
                qs = qs.filter(Status=2)
            else:
                qs = qs.exclude(Status=2)
        if "Today" in qp:
            qs = qs.filter(InsertTime__gt=datetime.now().strftime("%Y-%m-%d"))
        return qs

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
            "StatusMsg": "",
            "Status": 0,
        }
        order = serializer.create(data)
        order.save()
        return Response({"ID": order.ID})


class CTPOrderViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = CTPOrder.objects.all()
    serializer_class = CTPOrderSerializer


class CTPOrderDetailView(APIView):
    queryset = CTPOrder.objects.all()
    serializer_class = CTPOrderSerializer

    def _create_dummy_order(self, request):
        order = Order(
            Account=request.data['Account'],
            InstrumentID=request.data['InstrumentID'],
            Direction=request.data['Direction'],
            Offset=request.data['Offset'],
            Price=request.data['Price'],
            VolumesTotal=request.data['VolumesTotal'],
            VolumesTraded=request.data['VolumesTraded'],
            InsertTime=datetime.now(),
            SplitSleepAfterSubmit=0,
            SplitSleepAfterCancel=0,
            SplitPercent=1,
            Status=1,
            IsDummy=True,
        )
        order.save()
        return order

    def _create_dummy_ctporder(self, request, session_id, front_id, order_ref):
        ctp_order = CTPOrder(
            FrontID=front_id,
            SessionID=session_id,
            OrderRef=order_ref,
            OrderID=self._create_dummy_order(request),
            Account=request.data['Account'],
            InvestorID=request.data['InvestorID'],
            BrokerID=request.data['BrokerID'],
            InstrumentID=request.data['InstrumentID'],
            Direction=request.data['Direction'],
            Offset=request.data['Offset'],
            Price=request.data['Price'],
            VolumesTotal=request.data['VolumesTotal'],
            VolumesTraded=request.data['VolumesTraded'],
            InsertTime=datetime.now(),
            IsDummy=True,
        )
        ctp_order.save()
        return ctp_order

    def _partial_update(self, request, session_id, front_id, order_ref):
        try:
            obj = self.queryset.get(SessionID=session_id, FrontID=front_id, OrderRef=order_ref)
        except CTPOrder.DoesNotExist:
            obj = self._create_dummy_ctporder(request, session_id, front_id, order_ref)
        for field in CTPOrder._meta.fields:
            field_name = field.name
            if field_name in request.data:
                setattr(obj, field_name, request.data['field_name'])
            obj.save()
        return obj

    def _update_order_volumes(self, order):
        related_ctp_orders = self.queryset.filter(OrderID=order)
        volumes_traded = sum((o.VolumesTraded for o in related_ctp_orders), 0)
        order.VolumesTraded = volumes_traded
        if order.VolumesTraded == order.VolumesTotal and order.Status != 2:
            order.Status = 2
            order.CompleteTime = datetime.now()
        order.save()

    def get(self, request, session_id, front_id, order_ref):
        obj = get_object_or_404(self.queryset, SessionID=session_id, FrontID=front_id, OrderRef=order_ref)
        return Response(self.serializer_class(obj).data)

    def post(self, request, session_id, front_id, order_ref):
        """partial_update"""
        ctp_order = self._partial_update(request, session_id, front_id, order_ref)
        order = ctp_order.OrderID
        self._update_order_volumes(order)

        return Response({})


class CTPTradeViewSet(ModelViewSet):
    queryset = CTPTrade.objects.all()
    serializer_class = CTPTradeSerializer

    def create(self, request):
        ctp_order = get_object_or_404(CTPOrder.objects.all(), OrderSysID=request.data['OrderSysID'])
        request.data['CTPOrderID'] = ctp_order.id
        return super().create(request)


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

        lib = ac.get_library(f"bar.{freq}")
        date_range = DateRange(start_dt, end_dt)
        data = lib.read(contract, date_range=date_range)
        return data.to_dict(orient='index')


class QueryOrderFromCTPOrder(APIView):
    queryset = CTPOrder.objects.all()

    def get(self, request, session_id, front_id, order_ref):
        ctp_order = get_object_or_404(self.queryset, SessionID=session_id, FrontID=front_id, OrderRef=order_ref)
        return Response({"OrderID": ctp_order.OrderID.ID})


class Position(APIView):
    def get(self, request, pk=None):
        empty_position = {
            "TodayLOpen": 0,
            "TodayLClose": 0,
            "TodayLPosition": 0,
            "TodaySOpen": 0,
            "TodaySClose": 0,
            "TodaySPosition": 0,
            "YdLOpen": 0,
            "YdLClose": 0,
            "YdLPosition": 0,
            "YdSOpen": 0,
            "YdSClose": 0,
            "YdSPosition": 0,
            "TotalLPosition": 0,
            "TotalSPosition": 0,
            "NetAmount": 0,
        }
        data = {}
        keys = redis.hkeys(f"Position:{pk}")
        for key in keys:
            key = key.decode()
            position = empty_position.copy()
            position.update(ujson.loads(redis.hget(f"Position:{pk}", key)))
            data[key] = position
        return Response(data)


class TradeBot(CreateAPIView):
    schema = ManualSchema(fields=[
        coreapi.Field("account", True, "form", description="account name"),
    ])

    def post(self, request):
        account = request.data['account']
        path = CONFIG['api']['tradebot']['socket_path'].format(account=account)
        if os.path.exists(path):
            return Response({"OK": False})
        else:
            return Response({"OK": True, "url": f"ipc://{path}"})
