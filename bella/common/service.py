"""
服务状态监控
"""
import asyncio
from functools import wraps
from inspect import iscoroutinefunction
import os
import subprocess as sp
from quant.utils import Logger
from .db import redis
from .tables.service import Service
from .tables import mongo_to_dict
from .exception_handler import handle_exceptions


def status_monitor(name):
    """
    装饰器

    通过redis监控程序运行状态

    Parameters
    ==========
    name: str
        程序的唯一标识
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ioloop = asyncio.get_event_loop()
            ioloop.call_soon(heartbeat, name)
            if iscoroutinefunction(func):
                coro = func(*args, **kwargs)
                future = asyncio.ensure_future(coro)
                ioloop.run_until_complete(future)
            else:
                func(*args, **kwargs)
        return wrapper
    return decorator


def heartbeat(name, pid=None):
    loop = asyncio.get_event_loop()
    pid = pid or os.getpid()
    redis.set(f"KEY:STATUS:{name}", pid, ex=5)
    loop.call_later(2, heartbeat, name, pid)


class ServiceManager:
    """
    通过redis管理所有服务进程
    """
    def all_services(self):
        return set(Service.objects)

    def running_services(self):
        return set(filter(self.is_alive, self.all_services()))

    def stopped_services(self):
        return self.all_services() - self.running_services()

    def is_alive(self, service):
        if isinstance(service, dict):
            service = service['Name']
        elif isinstance(service, Service):
            service = service.Name
        return bool(redis.keys(f"KEY:STATUS:{service}"))

    @handle_exceptions()
    def shutdown(self, name):
        Logger.info(f"正在结束服务: {name}")
        service = Service.objects(Name=name).first()
        service.update(Status=False)
        pid = redis.get(f"KEY:STATUS:{name}")
        if not pid:
            raise RuntimeError(f"ServiceManager.shutdown:没有正在运行的服务: {name}")
        os.kill(int(pid), 9)

    @handle_exceptions()
    def start(self, name):
        Logger.info(f"正在启动服务: {name}")
        service = Service.objects(Name=name).first()
        service.update(Status=True)
        cmd = f"nohup {service.Command} > {service.LogFile} 2>&1 &"
        sp.Popen(cmd, shell=True)

    @handle_exceptions()
    def remove(self, name):
        if self.is_alive(name):
            self.shutdown(name)
        Logger.info(f"正在删除服务: {name}")
        Service.objects(Name=name).first().delete()

    @handle_exceptions()
    def create(self, data):
        service = Service(**data)
        service.save()

    @handle_exceptions()
    def modify(self, data):
        service = Service.objects(Name=data["Name"]).first()
        service.update(**data)
