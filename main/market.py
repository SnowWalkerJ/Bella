from datetime import datetime, date
import os
import ujson
import logging

from bella.asyncloop import ThreadSafeAsyncLoop
from bella.constants import CLIENT_DIR, SECOND_UNIT
from bella.crypt import PrpCrypt
from bella.ctp.market import Market
from bella.ctp.utils import struct_to_dict
from bella.db import redis
from bella.restful import API
from bella.exception_handler import handle_exceptions
from bella.service import status_monitor


logger = logging.getLogger("market")


class MarketServer(Market):
    def __init__(self, account):
        self.api = API()
        self.account = self.get_ctp_account(account)
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
            logger.debug(f"创建行情客户端 - {path}")
            self.RegisterFront(self.account['MdHost'].encode())
            logger.debug(f"注册前台服务器 {self.account['MdHost']}")
            self.Init()
            logger.debug("初始化")
            self.ioloop.run_forever()
        except KeyboardInterrupt:
            self.Release()
            self.ioloop.stop()

    def get_ctp_account(self, account):
        return self.api.action("ctp", "read", params={"Name": account})

    @handle_exceptions(ignore=True)
    def handler_data(self, data):
        try:
            instrument_id = data.InstrumentID.decode()
        except UnicodeDecodeError:
            return
        data = struct_to_dict(data)
        # hour = int(data['UpdateTime'].split(":")[0])
        if "03:00" <= data['UpdateTime'] <= "09:00" or "15:00" < data['UpdateTime'] <= "20:59":
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
            logger.error(f"time format error {date.today()} {data['UpdateTime']} {data['UpdateMillisec']}")
            raise

        channel = f"TICK:{instrument_id}"
        data = ujson.dumps(data)
        redis.publish(channel, data)
        redis.hset("Price", instrument_id, data)

    def OnRtnDepthMarketData(self, pDepthMarketData):
        self.add_callback(self.handler_data, pDepthMarketData)


if __name__ == '__main__':
    MarketServer("simnow").run()
