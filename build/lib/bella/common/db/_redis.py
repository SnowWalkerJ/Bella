import os
from redis import Redis
from aioredis import create_redis


REDIS_HOST   = os.environ.get("BELLA_REDIS_HOST", "localhost")
REDIS_PORT   = int(os.environ.get("BELLA_REDIS_PORT", "6379"))
REDIS_DB     = int(os.environ.get("BELLA_REDIS_DB", 0))
REDIS_PASSWD = os.environ.get("BELLA_REDIS_PASSWD")


redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWD
)

async def create_aredis():
    return await create_redis(
        address=(REDIS_HOST, REDIS_PORT),
        db=REDIS_DB,
        password=REDIS_PASSWD
    )
