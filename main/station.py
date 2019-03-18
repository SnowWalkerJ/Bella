"""
接收由Trader传来的redis消息，并做相应处理
"""
import asyncio

from aioredis.pubsub import Receiver
import ujson

from bella.restful import api
from bella.db._redis import create_aredis
from bella.service import status_monitor


class Station:
    def __init__(self):
        pass

    @status_monitor("station")
    async def run(self, loop):
        aredis = await create_aredis()
        recv = Receiver()
        await aredis.psubscribe(recv.pattern("Trader:*"))
        async for _, (channel, data) in recv.iter():
            cmd = channel.split(":")[1]
            if hasattr(self, cmd):
                data = ujson.loads(data)
                asyncio.ensure_future(getattr(self, cmd)(**data))

    async def OnRtnTrade(self, pTrade):
        api.action("trader", "on_rtn_trade", params={"pTrade": pTrade})
