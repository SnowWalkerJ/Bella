from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.views import APIView
from rest_framework.schemas import AutoSchema
from rest_framework.response import Response
from arctic.date import DateRange
import coreapi

# from bella.common.db._arctic import arctic
from .models.ctp_account import CTPAccount
from .models.service import Service
from .models.task import Task
from .models.bar_period import BarPeriod
from .models.instrument import Instrument
from .serializers import CTPAccountSerializer, ServiceSerializer, TaskSerializer, BarPeriodSerializer, InstrumentSerializer


class CTPAccountViewSet(ReadOnlyModelViewSet):
    queryset = CTPAccount.objects.all()
    serializer_class = CTPAccountSerializer


class BarPeriodViewSet(ReadOnlyModelViewSet):
    queryset = BarPeriod.objects.all()
    serializer_class = BarPeriodSerializer


class ServiceViewSet(ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class InstrumentView(APIView):
    schema = AutoSchema([
        coreapi.Field("data", True, "form", description="instrument data"),
    ])

    def put(self, request):
        data = request.data['data']
        old = list(Instrument.objects.all())
        old_ids = set(x['InstrumentId'] for x in old)
        serializer = InstrumentSerializer()
        for name, instrument in data.items():
            if name in old_ids:
                continue
            instrument = serializer.create(instrument)
            instrument.save()


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
