from apistar import http, exceptions, Route
import mongoengine
from ...common.crypt import PrpCrypt
from ...common.tables import Instrument, mongo_to_dict
from ...common.exception_handler import handle_exceptions


@handle_exceptions()
def list_():
    return [instrument.InstrumentID for instrument in Instrument.objects(IsTrading=1)]


@handle_exceptions()
def get(name: str):
    return Instrument.objects(InstrumentID=name).first()


@handle_exceptions()
def update(data: dict):
    new = list(data.keys())
    Instrument.objects(InstrumentID__nin=new).update(IsTrading=0)
    old = set(item["InstrumentID"] for item in Instrument.objects(IsTrading=1).only("InstrumentID"))
    diff = set(new) - old
    for name in diff:
        item = data[name]
        try:
            inst = Instrument(**item)
            inst.StrikePrice = 0.0
            inst.save()
        except Exception:
            print(item)
    return {"code": 200}


instruments_routes = [
    Route("/list", "GET", list_),
    Route("/update", "POST", update),
    Route("/get", "GET", get)
]
