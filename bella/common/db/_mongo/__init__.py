import os
from mongoengine import connect


MONGO_HOST   = os.environ.get("BELLA_MONGO_HOST", "localhost")
MONGO_PORT   = int(os.environ.get("BELLA_MONGO_PORT", "27017"))
MONGO_USER   = os.environ.get("BELLA_MONGO_USER")
MONGO_PASSWD = os.environ.get("BELLA_MONGO_PASSWD")

kwargs = {
    "host": MONGO_HOST,
    "port": MONGO_PORT
}
if MONGO_USER and MONGO_PASSWD:
    kwargs.update({
        "username": MONGO_USER,
        "password": MONGO_PASSWD
    })
connect("BELLA", **kwargs)
