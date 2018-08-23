from apistar import http, exceptions, Route
import mongoengine
from ...common.crypt import PrpCrypt
from ...common.db._mongo.tables import CTPAccount, mongo_to_dict


def list_():
    return [mongo_to_dict(account) for account in CTPAccount.objects]


def get(name: str):
    for account in CTPAccount.objects(Name=name):
        account = mongo_to_dict(account)
        return account
    raise exceptions.BadRequest("CTP账户不存在")


def create(data: dict) -> dict:
    """创建CTP账号"""
    crypt = PrpCrypt()
    data["Password"] = crypt.encrypt(data["Password"])
    try:
        instance = CTPAccount(**data)
    except mongoengine.FieldDoesNotExist as e:
        raise exceptions.ValidationError(str(e))
    instance.save()
    return {"code": 200}


def modify(data: dict):
    account = CTPAccount.objects(Name=data.pop("Name"))[0]
    if account.Password != data["Password"]:
        crypt = PrpCrypt()
        data["Password"] = crypt.encrypt(data["Password"])
    account.modify(**data)
    return {"code": 200}


def remove(name):
    """删除指定的CTP账号"""
    account = CTPAccount.objects(Name=name)[0]
    account.delete()
    return {"code": 200}


ctp_routes = [
    Route("/list", "GET", list_),
    Route("/get", "GET", get),
    Route("/create", "PUT", create),
    Route("/modify", "POST", modify),
    Route("/remove", "POST", remove),
]
