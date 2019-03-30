"""
服务状态监控
"""
import asyncio
from functools import wraps
from inspect import iscoroutinefunction
import os
import subprocess as sp
import logging

from .db import redis
from .exception_handler import handle_exceptions
from .restful import api


logger = logging.getLogger("service")


def status_monitor(name, loop=None):
    """
    装饰器

    通过redis监控程序运行状态

    Parameters
    ----------
    name: str
        程序的唯一标识
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal loop
            if loop is None:
                loop = asyncio.get_event_loop()
            else:
                asyncio.set_event_loop(loop)

            loop.call_soon(heartbeat, name)

            if iscoroutinefunction(func):
                coro = func(*args, **kwargs, loop=loop)
                loop.run_until_complete(coro)
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
        return api.action("service", "list")

    def running_services(self):
        return set(filter(self.is_alive, self.all_services()))

    def stopped_services(self):
        return self.all_services() - self.running_services()

    def is_alive(self, service):
        service = service['Name']
        return bool(redis.keys(f"KEY:STATUS:{service}"))

    @handle_exceptions()
    def shutdown(self, name):
        logger.info(f"正在结束服务: {name}")
        service = api.action("services", "read", {"Name": name})
        service.update(Status=False)
        api.action("services", "update", service)
        pid = redis.get(f"KEY:STATUS:{name}")
        if not pid:
            raise RuntimeError(f"ServiceManager.shutdown:没有正在运行的服务: {name}")
        os.kill(int(pid), 9)

    @handle_exceptions()
    def start(self, name):
        logger.info(f"正在启动服务: {name}")
        service = api.action("services", "read", {"Name": name})
        service.update(Status=True)
        api.action("services", "update", service)
        cmd = f"nohup {service['Command']} > {service['LogFile']} 2>&1 &"
        sp.Popen(cmd, shell=True)

    @handle_exceptions()
    def remove(self, name):
        if self.is_alive(name):
            self.shutdown(name)
        logger.info(f"正在删除服务: {name}")
        api.action("services", "delete", {"Name": name})

    @handle_exceptions()
    def create(self, data):
        api.action("services", "create", data)

    @handle_exceptions()
    def modify(self, data):
        # FIXME: location
        api.action("services", "update", data)
