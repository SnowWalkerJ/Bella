import asyncio

import zmq
import zmq.asyncio

from bella.service import status_monitor


@status_monitor("TradeBotTest", loop=zmq.asyncio.ZMQEventLoop())
async def run(loop):
    URL = "ipc:///tmp/tradebot.sock"
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.REQ)
    sock.connect(URL)
    await sock.send_json({
        "fn": "query_position",
        "kwargs": {"instrument": "c1905"},
    })
    msg = await sock.recv_json()
    print(msg)


if __name__ == "__main__":
    run()
