import os
from redis import Redis
from aioredis import create_redis

from ..config import CONFIG


config = CONFIG['db']['redis']


redis = Redis(
    host=config.get('host', 'localhost'),
    port=config.get('passowrd', 6379),
    db=config.get('db', 0),
    password=config.get('password'),
)

async def create_aredis(db=None, loop=None):
    return await create_redis(
        address=(config.get('host', 'localhost'), config.get('passowrd', 6379)),
        db=db or config.get('db', 0),
        password=config.get('password'),
        loop=loop
    )
