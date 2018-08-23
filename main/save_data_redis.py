from aioredis.pubsub import Receiver
import ujson
from startpro.core.utils.loader import safe_init_run
from startpro.core.process import Process
from bella.common.db._redis import create_aredis
from bella.common.service import status_monitor


class DataCacheSaver(Process):
    name = "data_cache_saver"

    @safe_init_run
    @status_monitor("data_save_redis")
    async def run(self, **kwargs):
        redis = await create_aredis()
        self.redis = await create_aredis()
        recv = Receiver()
        await redis.psubscribe(recv.pattern("TICK:*"), recv.pattern("BAR:*"))
        async for _, (channel, data) in recv.iter():
            if isinstance(channel, bytes):
                channel = channel.decode()
            channel = channel.split(":")
            d = ujson.loads(data)
            if channel[0] == "BAR":
                freq, instrument = channel[1:]
                key = f"ZSET:BAR:{freq}:{instrument}"
                score = d['timestamp']
            else:
                instrument = channel[1]
                key = f"ZSET:TICK:{instrument}"
                score = d['Timestamp']
            await self.redis.zadd(key, score, data)
