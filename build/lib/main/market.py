from datetime import datetime, date
import os
import ujson
from quant.utils import Logger
from startpro.core.utils.loader import safe_init_run
from bella.common.asyncloop import ThreadSafeAsyncLoop
from bella.common.constants import CLIENT_DIR, SECOND_UNIT
from bella.common.crypt import PrpCrypt
from bella.common.ctp.market import Market
from bella.common.ctp.utils import struct_to_dict
from bella.common.db import redis
from bella.common.restful import API
from bella.common.exception_handler import handle_exceptions
from bella.common.service import status_monitor


class MarketServer(Market):
    def __init__(self):
        self.api = API()
        self.account = self.get_ctp_account()
        super(MarketServer, self).__init__(
            self.account['UserID'].encode(),
            self.account['Password'].encode(),
            self.account['BrokerID'].encode())

    @status_monitor("market")
    def run(self):
        self.ioloop = ThreadSafeAsyncLoop()
        try:
            path = os.path.join(CLIENT_DIR, 'market')
            self.Create(path.encode())
            Logger.debug("创建行情客户端 -", path)
            self.RegisterFront(self.account['MdHost'].encode())
            Logger.debug("注册前台服务器", self.account['MdHost'])
            self.Init()
            Logger.debug("初始化")
            self.ioloop.run_forever()
        except KeyboardInterrupt:
            self.Release()
            self.ioloop.stop()

    def get_ctp_account(self):
        return self.api.action("ctp", "read", {"Name": "simnow"})

    @handle_exceptions(ignore=True)
    def handler_data(self, data):
        try:
            instrument_id = data.InstrumentID.decode()
        except UnicodeDecodeError:
            return
        data = struct_to_dict(data)
        # hour = int(data['UpdateTime'].split(":")[0])
        if "15:00" < data['UpdateTime'] <= "20:59":
            return
        del data["ExchangeID"], data["ExchangeInstID"], data["PreDelta"], \
            data["CurrDelta"], data["BidPrice2"], data["BidPrice3"], \
            data["BidPrice4"], data["BidPrice5"], \
            data["BidVolume2"], data["BidVolume3"], \
            data["BidVolume4"], data["BidVolume5"], \
            data["AskPrice2"], data["AskPrice3"], \
            data["AskPrice4"], data["AskPrice5"], \
            data["AskVolume2"], data["AskVolume3"], \
            data["AskVolume4"], data["AskVolume5"], data["ClosePrice"], \
            data["SettlementPrice"]
        data["InstrumentID"] = instrument_id
        data['TickTime'] = f"{date.today()} {data['UpdateTime']}.{data['UpdateMillisec']}"
        try:
            data['Timestamp'] = int(datetime.strptime(data['TickTime'], "%Y-%m-%d %H:%M:%S.%f").timestamp() * SECOND_UNIT)
        except ValueError:
            Logger.fatal("time format error", date.today(), data['UpdateTime'], data['UpdateMillisec'])
            raise

        channel = f"TICK:{instrument_id}"
        data = ujson.dumps(data)
        redis.publish(channel, data)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        self.add_callback(self.handler_data, pDepthMarketData)

@safe_init_run
def run(**kwargs):
    MarketServer().run()
