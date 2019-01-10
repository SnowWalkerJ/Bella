import ujson
from apistar.server.components import Component
from apistar.types import Type
from apistar import http
from ...common.exception_handler import handle_exceptions


class RequestData(Component):
    @handle_exceptions()
    def resolve(self, data: http.Body)->dict:
        return ujson.loads(data)
