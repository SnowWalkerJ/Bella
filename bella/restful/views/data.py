from arctic.date import DateRange
from apistar import http, exceptions, Route
from ...common.db._arctic import arctic


def bar(contract: str, freq: str, start_dt: str=None, end_dt: str=None):
    lib = arctic.get_library(f"bar.{freq}")
    date_range = DateRange(start_dt, end_dt)
    data = lib.read(contract, date_range=date_range)
    return data.to_dict(orient='index')


data_routes = [
    Route("/bar", 'GET', bar),
]
