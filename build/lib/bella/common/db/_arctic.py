import os
from arctic import Arctic
from arctic.auth import Credential
from arctic.hooks import register_get_auth_hook


ARCTIC_HOST = os.environ.get("BELLA_TICKS_HOST", "localhost")
ARCTIC_USER = os.environ.get("BELLA_TICKS_USER")
ARCTIC_PASSWD = os.environ.get("BELLA_TICKS_PASSWD")


def arctic_auth_hook(mongo_host, app, database):
    return Credential(
        database="arctic",
        user=ARCTIC_USER,
        password=ARCTIC_PASSWD,
    )


if ARCTIC_USER and ARCTIC_PASSWD:
    # 注册认证钩子
    register_get_auth_hook(arctic_auth_hook)


arctic = Arctic(ARCTIC_HOST)
