import zmq
import zmq.asyncio

from ..restful import api


class Trader:
    def __init__(self, account):
        URL = api.action("tradebot", "read", params={"id": account})['url']
        ctx = zmq.asyncio.Context()
        self.sock = ctx.socket(zmq.REQ)
        self.sock.connect(URL)
        self.account = account
        self.default_split_options = {
            "sleep_after_submit": 3,
            "sleep_after_cancel": 1,
            "split_percent": 0.2,
        }

    async def trade(self, function, instrument, price, volume, split_options=None):
        split_options = split_options or self.default_split_options
        data = {
            "fn": function,
            "kwargs": {
                "instrument": instrument,
                "price": price,
                "volume": volume,
                "split_options": split_options,
            }
        }
        await self.sock.send_json(data)
        resp = await self.sock.recv_json()
        return resp

    def buy(self, instrument, volume):
        return self.trade("buy", instrument, 'CP', volume)

    def buy_to_cover(self, instrument, volume):
        return self.trade("buy_to_cover", instrument, 'CP', volume)

    def sell(self, instrument, volume):
        return self.trade("sell", instrument, 'CP', volume)

    def sell_short(self, instrument, volume):
        return self.trade("sell_short", instrument, 'CP', volume)

    async def long(self, instrument, volume):
        position = await self.query_position(instrument)
        print(position)
        if not position['TodaySPosition'] and position['YdSPosition']:
            trade_volume = min(position['YdSPosition'], volume)
            volume -= trade_volume
            await self.buy_to_cover(instrument, trade_volume)
        if volume:
            await self.buy(instrument, volume)

    async def short(self, instrument, volume):
        position = await self.query_position(instrument)
        print(position)
        if not position['TodayLPosition'] and position['YdLPosition']:
            trade_volume = min(position['YdLPosition'], volume)
            volume -= trade_volume
            await self.sell(instrument, trade_volume)
        if volume:
            await self.sell_short(instrument, volume)

    async def query_position(self, instrument, account=None):
        data = {
            "fn": "query_position",
            "kwargs": {
                "account": account or self.account,
                "instrument": instrument,
            }
        }
        await self.sock.send_json(data)
        resp = await self.sock.recv_json()
        return resp
