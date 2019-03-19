"""
自动化交易机器人，实现拆单、对价单等高级功能
"""
import asyncio
from datetime import datetime

import ujson
import Pyro4
from dateutil.parser import parse
from aioredis.pubsub import Receiver

from bella.ctp.trader import Trader
from bella.ctp.utils import struct_to_dict
from bella.ctp._ctp import ApiStruct
from bella.restful import api
from bella.config import CONFIG
from bella.db._redis import redis, create_aredis
from bella.service import status_monitor


class TraderBot(Trader):

    ############## 通知

    def OnRtnTrade(self, pTrade):
        """成交通知"""
        redis.publish("Trader:OnRtnTrade", ujson.dumps({"pTrade": struct_to_dict(pTrade)}))
        super().OnRtnTrade(pTrade)
        # Submit to API
        data = {
            "TradeID": pTrade.TradeID.decode(),
            "OrderID": self.query_ctp_order(pTrade.BrokerID, pTrade.InvestorID, pTrade.OrderRef),
            "Price": pTrade.Price,
            "Volume": pTrade.Volume,
            "TradeTime": parse(b" ".join([pTrade.TradeDate, pTrade.TradeTime]).decode()),
        }
        api.action("ctp_trade", params=data, action="POST")
        self.query_position(pTrade.InstrumentID)

    def OnRtnOrder(self, pOrder):
        """
        报单通知（通过参数检测->已经提交成功）
        """
        redis.publish("Trader:OnRtnOrder", ujson.dumps(struct_to_dict(pOrder)))
        super().OnRtnOrder(pOrder)

    def OnRtnInstrumentStatus(self, pInstrumentStatus):
        """合约交易状态通知"""
        redis.publish("Trader:OnRtnInstrumentStatus", ujson.dumps(struct_to_dict(pInstrumentStatus)))
        super().OnRtnInstrumentStatus(pInstrumentStatus)

    def OnRtnTradingNotice(self, pTradingNoticeInfo):
        """交易通知"""
        redis.publish("Trader:OnRtnTradingNotice", ujson.dumps(struct_to_dict(pTradingNoticeInfo)))
        super().OnRtnTradingNotice(pTradingNoticeInfo)

    ############## 回报

    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        """报单操作请求响应"""
        data = {
            "pInputOrderAction": struct_to_dict(pInputOrderAction),
            "pRspInfo": struct_to_dict(pRspInfo),
            "nRequestID": nRequestID,
            "bIsLast": bIsLast,
        }
        redis.publish("Trader:OnRspOrderAction", ujson.dumps(data))
        super().OnRspOrderAction(pInputOrderAction, pRspInfo, nRequestID, bIsLast)

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        """请求查询资金账户响应"""
        data = {
            "pTradingAccount": struct_to_dict(pTradingAccount),
            "pRspInfo": struct_to_dict(pRspInfo),
            "nRequestID": nRequestID,
            "bIsLast": bIsLast,
        }
        redis.publish("Trader:OnRspQryTradingAccount", ujson.dumps(data))
        super().OnRspQryTradingAccount(pTradingAccount, pRspInfo, nRequestID, bIsLast)

    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者响应"""
        data = {
            "pInvestor": struct_to_dict(pInvestor),
            "pRspInfo": struct_to_dict(pRspInfo),
            "nRequestID": nRequestID,
            "bIsLast": bIsLast,
        }
        redis.publish("Trader:OnRspQryInvestor", ujson.dumps(data))
        super().OnRspQryInvestor(pInvestor, pRspInfo, nRequestID, bIsLast)

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者持仓响应"""
        pInvestor = struct_to_dict(pInvestor)
        # Redis Publish
        data = {
            "pInvestorPosition": pInvestor,
            "pRspInfo": struct_to_dict(pRspInfo),
            "nRequestID": nRequestID,
            "bIsLast": bIsLast,
        }
        redis.publish("Trader:OnRspQryInvestorPosition", ujson.dumps(data))

        # Redis Status
        redis.hset(Position, pInvestor['InstrumentID'], pInvestor)

        super().OnRspQryInvestorPosition(pInvestorPosition, pRspInfo, nRequestID, bIsLast)

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者仓位明细响应"""
        data = {
            "pInvestorPositionDetail": struct_to_dict(pInvestor),
            "pRspInfo": struct_to_dict(pRspInfo),
            "nRequestID": nRequestID,
            "bIsLast": bIsLast,
        }
        redis.publish("Trader:OnRspQryInvestorPositionDetail", ujson.dumps(data))
        super().OnRspQryInvestorPositionDetail(pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast)

    def send_order(self, instrument, price, volume, direction, offset, order_id):
        orderref = self.inc_orderref_id()
        order = ApiStruct.InputOrder(
            BrokerID=self.broker_id,
            InvestorID=self.investor_id,
            InstrumentID=instrument.encode(),
            OrderRef=str(orderref),
            UserID=self.investor_id,
            OrderPriceType=ApiStruct.OPT_LimitPrice,
            LimitPrice=price,
            VolumeTotalOriginal=volume,
            Direction=direction,
            CombOffsetFlag=offset,
            CombHedgeFlag=ApiStruct.HF_Speculation,
            ContingentCondition=ApiStruct.CC_Immediately,
            ForceCloseReason=ApiStruct.FCC_NotForceClose,
            IsAutoSuspend=0,
            TimeCondition=ApiStruct.TC_GFD,
            UserForceClose=0,
            VolumeCondition=ApiStruct.VC_AV,
            MinVolume=1,
        )
        self.ReqOrderInsert(order, self.inc_request_id())

        # API
        record = {
            'BrokerID': int(record.BrokerID),
            'InvestorID': int(record.InvestorID),
            'OrderRef': orderref,
            'OrderID': order_id,
            'InstrumentID': instrument,
            'Direction': direction,
            'Offset': offset,
            'Price': price,
            'Volume': volume,
            'InsertTime': datetime.now(),
        }

        api.action("ctp_order", params=record, action="POST")
        return orderref

    def cancel_order(self, instrument, order_ref, front_id, session_id):
        """
        撤单
        """
        req = ApiStruct.InputOrderAction()
        req.InstrumentID = instrument
        req.OrderRef = order_ref
        req.FrontID = front_id
        req.SessionID = session_id

        req.ActionFlag = ApiStruct.AF_Delete  # 删除
        req.BrokerID = self.broker_id
        req.InvestorID = self.investor_id
        req.UserID = self.investor_id
        self.ReqOrderAction(req, self.inc_request_id())

    def query_position(self, instrument):
        req = ApiStruct.QryInvestorPosition(BrokerID=self.broker_id,
                                            InvestorID=self.investor_id,
                                            InstrumentID=instrument)
        self.ReqQryInvestorPosition(req, self.inc_request_id())


@Pyro4.behavior(instance_mode="single")
class TraderInterface:
    """
    交易端的交互界面。通过redis收发消息
    """
    def __init__(self):
        account = api.action("ctp", "read", params={"Name": "simnow"})
        self.trader = TraderBot(account['TdHost'].encode(),
                                account['UserID'].encode(),
                                account['BrokerID'].encode(),
                                account['Password'].encode())

    @Pyro4.expose
    def query_position(self, instrument):
        return ujson.loads(redis.hget("Position", instrument))

    @Pyro4.expose
    def query_price(self, instrument):
        return float(redis.hget("Price", instrument))

    @Pyro4.expose
    def buy(self, instrument, price, volume):
        order_id = self.insert_order(instrument, price, volume, ApiStruct.D_Buy, ApiStruct.OF_Open)
        return self.trader.send_order(instrument, price, volume, ApiStruct.D_Buy, ApiStruct.OF_Open, order_id)

    @Pyro4.expose
    def buy_to_cover(self, instrument, price, volume):
        order_id = self.insert_order(instrument, price, volume, ApiStruct.D_Buy, ApiStruct.OF_Close)
        return self.trader.send_order(instrument, price, volume, ApiStruct.D_Buy, ApiStruct.OF_Close, order_id)

    @Pyro4.expose
    def sell_short(self, instrument, price, volume):
        order_id = self.insert_order(instrument, price, volume, ApiStruct.D_Sell, ApiStruct.OF_Open)
        return self.trader.send_order(instrument, price, volume, ApiStruct.D_Sell, ApiStruct.OF_Open, order_id)

    @Pyro4.expose
    def sell(self, instrument, price, volume):
        order_id = self.insert_order(instrument, price, volume, ApiStruct.D_Sell, ApiStruct.OF_Close)
        return self.trader.send_order(instrument, price, volume, ApiStruct.D_Sell, ApiStruct.OF_Close, order_id)

    def insert_order(self, instrument, price, volume, direction, offset):
        data = {
            "InstrumentID": instrument,
            "Direction": direction.decode(),
            "Offset": offset.decode(),
            "Price": price,
            "Volume": volume,
        }
        resp = api.action("order", "create", params=data)
        return resp['ID']


if __name__ == "__main__":
    TraderInterface().run()
