try:
    import ujson as json
except ImportError:
    import json

from ..db._redis import create_aredis


class Market:
    def __init__(self):
        self._redis = None

    async def get_redis(self):
        if self._redis is None:
            self._redis = await create_aredis()
        return self._redis

    def subscribe_bar(self, instrument, freq):
        channel = "BAR:{freq}:{instrument}"
        return self._subscribe(channel)

    def subscribe_tick(self, instrument):
        channel = f"TICK:{instrument}"
        return self._subscribe(channel)

    async def _subscribe(self, channel):
        redis = await self.get_redis()
        ch = await redis.subscribe(channel)
        while await ch.wait_message():
            msg = await ch.get()
            data = json.loads(msg)
            yield data
