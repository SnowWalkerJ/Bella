from apistar import Include
from .views.ctp import ctp_routes
from .views.data import data_routes
from .views.futures import futures_routes
from .views.instruments import instruments_routes
from .views.services import services_routes


routes = [
    Include("/futures", name="futures", routes=futures_routes),
    Include("/ctp", name="ctp", routes=ctp_routes),
    Include("/data", name="data", routes=data_routes),
    Include("/instruments", name="instruments", routes=instruments_routes),
    Include("/services", name="services", routes=services_routes),
]
routes.append(Include("/api", name="api", routes=routes.copy()))
