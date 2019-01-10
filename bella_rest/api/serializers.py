from rest_framework.serializers import ModelSerializer

from .models.ctp_account import CTPAccount
from .models.service import Service
from .models.task import Task
from .models.instrument import Instrument
from .models.bar_period import BarPeriod


class CTPAccountSerializer(ModelSerializer):
    class Meta:
        model = CTPAccount
        fields = '__all__'


class ServiceSerializer(ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class InstrumentSerializer(ModelSerializer):
    class Meta:
        model = Instrument
        fields = '__all__'



class TaskSerializer(ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class BarPeriodSerializer(ModelSerializer):
    class Meta:
        model = BarPeriod
        fields = '__all__'
