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
        "fn": "sell",
        "kwargs": {
            "instrument": "c1905",
            "volume": 11,
            "price": "CP",
            "split_options": {
                "sleep_after_submit": 5,
                "sleep_after_cancel": 5,
                "split_percent": 0.3
            }
        },
    })
    print(await sock.recv_json())

    await sock.send_json({
        "fn": "query_position",
        "kwargs": {"instrument": "c1905"},
    })
    print(await sock.recv_json())


if __name__ == "__main__":
    run()
