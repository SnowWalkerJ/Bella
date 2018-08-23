from apistar import http, exceptions, Route
import mongoengine
from ...common.crypt import PrpCrypt
from ...common.db._mongo.tables import Futures, mongo_to_dict


def list_():
    return [mongo_to_dict(futures) for futures in Futures.objects]


def get(name: http.QueryParam):
    for futures in Futures.objects(name=name):
        data = mongo_to_dict(futures)
        return data
    raise exceptions.BadRequest("指定合约不存在")


def create(data: dict):
    instance = Futures(**data)
    instance.save()
    return {"code": 200}


def modify(data: dict):
    account = Futures.objects(name=data["name"]).first()
    account.modify(**data)
    return {"code": 200}


def delete(name: str):
    account = Futures.objects(name=name).first()
    account.delete()
    return {"code": 200}


futures_routes = [
    Route("/list", "GET", list_),
    Route("/get", "GET", get),
    Route("/create", "PUT", create),
    Route("/modify", "POST", modify),
    Route("/delete", "POST", delete),
]
