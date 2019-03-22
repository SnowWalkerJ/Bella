"""
自动化交易机器人，实现拆单、对价单等高级功能
"""
import asyncio
from datetime import datetime

import ujson
from dateutil.parser import parse
from aioredis.pubsub import Receiver
import zmq
import zmq.asyncio

from bella.ctp.trader import Trader
from bella.ctp.utils import struct_to_dict
from bella.ctp._ctp import ApiStruct
from bella.restful import api
from bella.config import CONFIG
from bella.db._redis import redis, create_aredis
from bella.service import status_monitor


class TradingAPI:
    # TODO: query_order, query_ctp_order
    @staticmethod
    def insert_order(instrument, price, volume, direction, offset, split_options):
        data = {
            "InstrumentID": instrument,
            "Direction": direction.decode(),
            "Offset": offset.decode(),
            "Price": str(price),
            "VolumesTotal": volume,
            "VolumesTraded": 0,
            "InsertTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "SplitSleepAfterSubmit": split_options['sleep_after_submit'],
            "SplitSleepAfterCancel": split_options['sleep_after_cancel'],
            "SplitPercent": split_options['split_percent'],
            "Finished": False,
        }
        resp = api.action("order", "create", params=data)
        return resp['ID']

    @staticmethod
    def insert_ctp_order(order_id, pInputOrder):
        data = {
            "BrokerID": pInputOrder.BrokerID.decode(),
            "InvestorID": pInputOrder.InvestorID.decode(),
            "OrderRef": pInputOrder.OrderRed.decode(),

            "OrderID": order_id,

            "InstrumentID": pInputOrder.InstrumentID.decode(),
            "Direction": pInputOrder.Direction.decode(),
            "Offset": pInputOrder.CombOffsetFlag.decode(),
            "Price": pInputOrder.LimitPrice,
            "VolumesTotal": pInputOrder.VolumeTotalOriginal,
            "VolumesTraded": 0,
            "InsertTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Finished": False,
        }
        resp = api.action("ctp_order", "create", params=data)

    @classmethod
    def insert_ctp_trade(cls, pTrade):
        data = {
            "TradeID": pTrade.TradeID.decode(),
            "CTPOrderID": cls.query_ctp_order(pTrade.BrokerID, pTrade.InvestorID, pTrade.OrderRef),
            "Price": pTrade.Price,
            "Volume": pTrade.Volume,
            "TradeTime": b" ".join([pTrade.TradeDate, pTrade.TradeTime]).decode(),
        }
        api.action("ctp_trade", "create", params=data)

    @classmethod
    def update_ctp_order(cls, pOrder):
        order_id = cls.query_order(pOrder.OrderRef.decode())
        complete_time = cancel_time = None
        if pOrder.VolumesTotal == 0:
            complete_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if pOrder.CancelTime:
            cancel_time = b" ".join([pOrder.TradingDay, pOrder.CancelTime]).decode()
        update_time = b" ".join([pOrder.TradingDay, pOrder.UpdateTime]).decode()
        finished = bool(complete_time or cancel_time)
        data = {
            'id': pOrder.OrderRef.decode(),
            # 'BrokerID': pOrder.BrokerID.decode(),
            # 'InvestorID': pOrder.InvestorID.decode(),
            # 'OrderRef': pOrder.OrderRef.decode(),
            # 'OrderID': order_id,
            # 'InstrumentID': pOrder.InstrumentID.decode(),
            # 'Direction': pOrder.Direction.decode(),
            # 'Offset': pOrder.Offset.decode(),
            # 'Price': pOrder.LimitPrice,
            # 'VolumesTotal': pOrder.VolumeTotalOriginal,
            # 'FrontID': pOrder.FrontID.decode(),
            'VolumesTraded': pOrder.VolumesTraded,
            'UpdateTime': update_time,
            'CompleteTime': complete_time,
            'CancelTime': cancel_time,
            'StatusMsg': pOrder.StatusMsg.decode(),
            'Finished': finished,
        }
        api.action("ctp_order", "partial_update", params=data)


class TraderBot(Trader):

    ############## 通知

    def OnRtnTrade(self, pTrade):
        """成交通知"""
        redis.publish("Trader:OnRtnTrade", ujson.dumps({"pTrade": struct_to_dict(pTrade)}))
        super().OnRtnTrade(pTrade)
        TradingAPI.insert_ctp_trade(pTrade)
        self.query_position(pTrade.InstrumentID)

    def OnRtnOrder(self, pOrder):
        """
        报单通知（通过参数检测->已经提交成功）
        """
        # redis.publish("Trader:OnRtnOrder", ujson.dumps(struct_to_dict(pOrder)))
        TradingAPI.update_ctp_order(pOrder)
        super().OnRtnOrder(pOrder)

    def OnRtnInstrumentStatus(self, pInstrumentStatus):
        """合约交易状态通知"""
        # redis.publish("Trader:OnRtnInstrumentStatus", ujson.dumps(struct_to_dict(pInstrumentStatus)))
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
            OrderRef=str(orderref).encode(),
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
        TradingAPI.insert_ctp_order(order_id, order)
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


class RedisDB:
    def add_task(self, order_id, instrument, price, volume, direction, offset, split_options):
        data = {
            "order_id": order_id,
            "instrument": instrument,
            "price": price,
            "volume": volume,
            "direction": direction,
            "offset": offset,
            "split_options": ujson.dumps(split_options),
        }
        redis.hmset("Trader:Task", order_id, ujson.dumps(data))

    def list_tasks(self):
        return redis.hkeys("Trader:Task")

    def get_task(self, order_id):
        return ujson.loads(redis.hget("Trader:Task", order_id))

    def remove_task(self, order_id):
        redis.hdel("Trader:Task", order_id)


class TaskManager:
    def __init__(self, trader: TraderBot, loop: asyncio.AbstractEventLoop):
        self.trader = trader
        self.loop = loop
        self.db = RedisDB()

    def submit(self, task):
        if task['split_options'] is None:
            task['split_options'] = {
                "sleep_after_submit": 1,
                "sleep_after_cancel": 1,
                "split_percent": 1,
            }
        self.db.add_task(*task)
        asyncio.ensure_future(self.trade(task['order_id']), loop=self.loop)

    async def trade(self, order_id):
        task = self.db.get_task(order_id)
        if task['volume'] == 0:
            self.db.remove_task(order_id)
            return
        trade_volume = self.decide_volume(task['volume'], task['split_options'])
        price = self.decide_price(task['instrument'], task['price'])
        orderref = self.trader.send_order(task['instrument'], price, trade_volume, task['direction'], task['offset'], order_id)
        await asyncio.sleep(split_options['sleep_after_submit'], loop=self.loop)
        self.trader.cancel_order(task['instrument'], order_ref, self.trader.front_id, self.trader.session_id)
        await asyncio.sleep(split_options['sleep_after_cancel'], loop=self.loop)
        await self.trade(order_id)

    @staticmethod
    def decide_volume(total_volume, split_options):
        percent = split_options['split_percent']
        volume = min(max(round(percent * total_volume), 1), total_volume)
        return volume

    def decide_price(instrument, direction, price):
        current_prices = ujson.loads(redis.hget("Price", instrument))
        if price == "CP":
            return current_prices['BidPrice1'] if direction == ApiStruct.D_Buy else current_prices['AskPrice1']
        elif price == "ASK":
            return current_prices['AskPrice1']
        elif price == "BID":
            return current_prices['BidPrice1']
        elif price == "LAST":
            return current_prices['LastPrice']
        elif price == "MID":
            return (current_prices['BidPrice1'] + current_prices['AskPrice1']) / 2
        else:
            try:
                price = float(price)
            except ValueError as e:
                raise ValueError(f"Invalid price: {price}") from e
        return price


class TraderInterface:
    """
    交易端的交互界面。通过redis收发消息
    """

    EXPOSED_METHODS = [
        "query_position",
        "query_price",
        "buy",
        "buy_to_cover",
        "sell",
        "sell_short"
    ]

    def __init__(self):
        account = api.action("ctp", "read", params={"Name": "simnow"})
        self.trader = TraderBot(account['TdHost'].encode(),
                                account['UserID'].encode(),
                                account['BrokerID'].encode(),
                                account['Password'].encode())

    def query_position(self, instrument):
        return ujson.loads(redis.hget("Position", instrument))

    def query_price(self, instrument):
        return ujson.loads(redis.hget("Price", instrument))

    def buy(self, instrument, price, volume, split_options=None):
        direction, offset = ApiStruct.D_Buy, ApiStruct.OF_Open
        return self.transaction_split(instrument, price, volume, direction, offset, split_options)

    def buy_to_cover(self, instrument, price, volume, split_options=None):
        direction, offset = ApiStruct.D_Buy, ApiStruct.OF_Close
        return self.transaction_split(instrument, price, volume, direction, offset, split_options)

    def sell_short(self, instrument, price, volume, split_options=None):
        direction, offset = ApiStruct.D_Sell, ApiStruct.OF_Open
        return self.transaction_split(instrument, price, volume, direction, offset, split_options)

    def sell(self, instrument, price, volume, split_options=None):
        direction, offset = ApiStruct.D_Sell, ApiStruct.OF_Close
        return self.transaction_split(instrument, price, volume, direction, offset, split_options)

    def transaction_split(self, instrument, price, volume, direction, offset, split_options):
        order_id = TradingAPI.insert_order(instrument, price, volume, direction, offset, split_options)
        self.task_queue.append((order_id, instrument, price, volume, direction, offset, split_options))
        asyncio.sleep(0.01, loop=self.loop)
        return {'order_id': order_id}


    @status_monitor("TradeBot", loop=zmq.asyncio.ZMQEventLoop())
    async def run(self, loop):
        self.loop = loop
        URL = "ipc:///tmp/tradebot.sock"
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.REP)
        sock.connect(URL)
        asyncio.ensure_future(self.manage_tasks(loop), loop=loop)
        while 1:
            data = await sock.recv_json()
            fn_name = data['fn']
            kwargs = data['kwargs']
            if fn_name not in self.EXPOSED_METHODS:
                await sock.send(b"NotAllowed")
                continue
            fn = getattr(self, fn_name)
            result = fn(**kwargs)
            await sock.send_json(result)


if __name__ == "__main__":
    TraderInterface().run()
