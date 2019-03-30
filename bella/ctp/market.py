import logging

from ._ctp import ApiStruct, MdApi
from .utils import struct_to_dict
from ..restful import api


logger = logging.getLogger("market")


class Market(MdApi):
    def __init__(self, user_id, pass_wd, broker_id):
        self.request_id = 0
        self.user_id = user_id
        self.pass_wd = pass_wd
        self.broker_id = broker_id
        self.instrument = set()
        self.tick_data = []
        self.__ioloop = None

    ############# 主动API

    def get_contracts(self):
        return api.action("instruments", "list", params={}, action="GET")

    def subscribe(self):
        """
        Loggerin and init required
        """
        flag = self.SubscribeMarketData([x.encode() for x in self.get_contracts()])
        logger.info(f'SubscribeMarketData status:[{flag}]')

    def handler_data(self, data):
        pass

    def inc_request_id(self):
        self.request_id += 1
        return self.request_id

    def add_callback(self, *args, **kwargs):
        if not self.ioloop:
            logger.warn("IOLoop not set")
            return
        return self.ioloop.call_soon(*args, **kwargs)

    def add_callback_at(self, when, *args, **kwargs):
        if not self.ioloop:
            logger.warn("IOLoop not set")
            return
        return self.ioloop.call_at(when, *args, **kwargs)

    ############# 前台连接

    def OnFrontConnected(self):
        req = ApiStruct.ReqUserLogin(BrokerID=self.broker_id, UserID=self.user_id, Password=self.pass_wd)
        r = self.ReqUserLogin(req, self.inc_request_id())
        logger.info('OnFrontConnected status:[%s]' % r)

    def OnFrontDisconnected(self, nReason):
        logger.warn('OnFrontDisconnected:[%s]' % nReason)
        # refresh api connection

    ############## 通知

    def OnRtnDepthMarketData(self, pDepthMarketData):
        self.add_callback(self.handler_data, pDepthMarketData)
        logger.info('OnRtnDepthMarketData:[%s] at:[%s]' % (pDepthMarketData.InstrumentID, pDepthMarketData.UpdateTime))

    ############## 回报

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        logger.info('OnRspUserLogin:[%s]' % struct_to_dict(pRspInfo))
        logger.info('GetTradingDay:[%s]' % self.GetTradingDay())
        logger.info('GetApiVersion:[%s]' % self.GetApiVersion())
        if pRspInfo.ErrorID == 0:
            # subscribe market data
            self.subscribe()
        else:
            logger.error("Login failure:[%s] msg:[%s]" % (pRspInfo.ErrorID, pRspInfo.ErrorMsg.decode("gbk")))

    def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
        # logger.info('OnRspSubMarketData:[%s]', pRspInfo.ErrorID)
        # print(pSpecificInstrument, pRspInfo)
        pass

    ############## 错误

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        logger.error('OnRspError:[%s] of [%s]' % (struct_to_dict(pRspInfo), nRequestID))

    ############## 属性

    @property
    def ioloop(self):
        return self.__ioloop

    @ioloop.setter
    def ioloop(self, loop):
        self.__ioloop = loop
