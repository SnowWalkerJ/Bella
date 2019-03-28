import asyncio

import zmq
import zmq.asyncio

from bella.service import status_monitor


@status_monitor("TradeBotTest", loop=zmq.asyncio.ZMQEventLoop())
async def run(loop):
    URL = "ipc:///tmp/tradebot.sock"
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.REP)
    sock.connect(URL)
    await sock.send_json({
        "fn": "query_position",
        "kwargs": {"instrument": "c1905"},
    })
