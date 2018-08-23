"""
Restful API
"""
import urllib
import requests
import inspect
import ujson
from .config import CONFIG


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, req):
        req.headers["Authorization"] = f"Token {self.token}"
        return req


class RequestError(BaseException):
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason

    def __str__(self):
        return f"[{self.code}] {self.reason}"

    def __repr__(self):
        return f"[{self.code}] {self.reason}"


class APIMethod:
    def __init__(self):
        self.method = None

    def __set_name__(self, owner, method):
        self.method = method

    def __get__(self, obj, type=None):
        if type is None:
            return self
        def request(uri, *args, **kwargs):
            url = urllib.parse.urljoin(obj.root_url, uri)
            func = getattr(obj.session, self.method)
            sig = inspect.signature(func).bind(url, *args, **kwargs).arguments
            if "data" in sig:
                sig["data"] = ujson.dumps(sig["data"])
            if "kwargs" in sig:
                sig.update(sig.pop("kwargs"))
            req = func(auth=obj.auth, **sig)
            if req.status_code != 200:
                raise RequestError(req.status_code, req.reason)
            return req.json()
        return request


class RestAPI:
    get    = APIMethod()
    post   = APIMethod()
    put    = APIMethod()
    delete = APIMethod()

    def __init__(self, host, port, root="/", token=""):
        self.root_url = f"http://{host}:{port}/{root}"
        self.session = requests.Session()
        self.auth = TokenAuth(token)
        self.session.headers.update({"Content-Type": "application/json"})


API_HOST = CONFIG.API_HOST
API_PORT = CONFIG.get("API_PORT", 9999)
API_ROOT = CONFIG.get("API_ROOT", "/")
API_AUTH = CONFIG.get("API_AUTH", "")
API = RestAPI(API_HOST, API_PORT, API_ROOT, API_AUTH)
