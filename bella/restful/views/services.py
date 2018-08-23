from apistar import Route
from ...common.db._redis import redis
from ...common.db._mongo.tables import mongo_to_dict
from ...common.service import ServiceManager


def list_() -> list:
    sm = ServiceManager()
    services = []
    for item in sm.all_services():
        item = mongo_to_dict(item)
        if item["Status"]:
            if sm.is_alive(item):
                item["Status"] = "正常运行"
            else:
                item["Status"] = "异常退出"
        else:
            item["Status"] = "停止"
        services.append(item)
    return services


def shutdown(name: str):
    sm = ServiceManager()
    try:
        sm.shutdown(name)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


def reboot(name, str):
    sm = ServiceManager()
    try:
        sm.shutdown(name)
        sm.start(name)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


def start(name: str):
    sm = ServiceManager()
    try:
        sm.start(name)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


def delete(name: str):
    sm = ServiceManager()
    try:
        sm.remove(name)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


def create(data: dict):
    sm = ServiceManager()
    data["Status"] = False
    try:
        sm.create(data)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


def modify(data: dict):
    sm = ServiceManager()
    try:
        sm.modify(data)
    except Exception as e:
        return {"code": 500, "message": repr(e)}
    return {"code": 200}


services_routes = [
    Route("/create", "POST", create),
    Route("/modify", "POST", modify),
    Route("/list", "GET", list_),
    Route("/start", "POST", start),
    Route("/shutdown", "POST", shutdown),
    Route("/reboot", "POST", reboot),
    Route("/delete", "POST", delete),
]
