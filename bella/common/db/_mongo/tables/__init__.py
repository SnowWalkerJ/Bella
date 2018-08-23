from decimal import Decimal
from .ctp_account import CTPAccount
from .futures import Futures
from .instrument import Instrument


def mongo_to_dict(obj):
    d = {}
    for key in obj._fields.keys():
        v = getattr(obj, key)
        if isinstance(v, Decimal):
            v = float(v)
        d[key] = v
    return d
