"""
自动化交易机器人，实现拆单、对价单等高级功能
"""
import asyncio
from datetime import datetime

import ujson
import zmq
import zmq.asyncio

from bella.ctp.trader import Trader
from bella.ctp.utils import struct_to_dict
from bella.ctp._ctp import ApiStruct
from bella.restful import api
from bella.config import CONFIG
from bella.db._redis import redis, create_aredis
from bella.service import status_monitor

# TODO: logger


class OrderStatus:
    INACTIVE = 0
    RUNNING = 1
    FINISHED = 2


def reformat_date(trading_day, time):
    trading_day = trading_day.decode()
    time = time.decode()
    year = trading_day[:4]
    month = trading_day[4:6]
    day = trading_day[-2:]
    date = "-".join((year, month, day))
    return " ".join((date, time))


class TradingAPI:
    @staticmethod
    def get_ctp_order(orderref):
        return api.action("ctp_order", "read", params={"OrderRef": orderref})

    @staticmethod
    def insert_order(account, instrument, price, volume, direction, offset, split_options):
        data = {
            "Account": account,
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
            "Status": OrderStatus.INACTIVE,
        }
        resp = api.action("order", "create", params=data)
        return resp['ID']

    @staticmethod
    def insert_ctp_order(account, order_id, pInputOrder, front_id):
        data = {
            "Account": account,

            "BrokerID": pInputOrder.BrokerID.decode(),
            "InvestorID": pInputOrder.InvestorID.decode(),
            "OrderRef": pInputOrder.OrderRef.decode(),

            "OrderID": order_id,

            "FrontID": front_id,
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

    @staticmethod
    def insert_ctp_trade(account, pTrade):
        data = {
            "Account": account,
            "TradeID": pTrade.TradeID.decode(),
            "CTPOrderID": pTrade.OrderRef.decode(),
            "Price": pTrade.Price,
            "Volume": pTrade.Volume,
            "TradeTime": reformat_date(pTrade.TradeDate, pTrade.TradeTime)
        }
        api.action("ctp_trade", "create", params=data)

    @classmethod
    def update_ctp_order(cls, pOrder):
        try:
            order_id = cls.query_order(pOrder.OrderRef.decode())
        except ValueError:
            return
        complete_time = cancel_time = None
        if pOrder.VolumeTotal == 0:
            complete_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if pOrder.StatusMsg.decode("gbk") == "已撤单":
            cancel_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        update_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        finished = bool(complete_time or cancel_time)
        data = {
            'OrderRef': pOrder.OrderRef.decode(),
            'VolumesTraded': pOrder.VolumeTraded,
            'UpdateTime': update_time,
            'CompleteTime': complete_time,
            'CancelTime': cancel_time,
            'StatusMsg': pOrder.StatusMsg.decode("gbk"),
            'Finished': finished,
        }
        api.action("ctp_order", "partial_update", params=data)

    @staticmethod
    def query_order(orderref):
        rsp = api.action("query_order_from_ctporder", "read", params={"id": int(orderref)})
        if rsp:
            return rsp['OrderID']
        else:
            raise ValueError(f"Can't find CTPOrder {orderref}")


class TraderBot(Trader):
    def __init__(self, account_name):
        self.account_name = account_name
        account_info = api.action("ctp", "read", params={"Name": account_name})
        super().__init__(account_info['TdHost'].encode(),
                         account_info['UserID'].encode(),
                         account_info['BrokerID'].encode(),
                         account_info['Password'].encode())

    ############## 通知

    def OnRtnTrade(self, pTrade):
        """成交通知"""
        redis.publish("Trader:OnRtnTrade", ujson.dumps({"pTrade": struct_to_dict(pTrade)}))
        # super().OnRtnTrade(pTrade)
        TradingAPI.insert_ctp_trade(self.account_name, pTrade)
        self.getPosition()
        self.getAccount()
        self.getInvestor()

    def OnRtnOrder(self, pOrder):
        """
        报单通知（通过参数检测->已经提交成功）
        """
        # redis.publish("Trader:OnRtnOrder", ujson.dumps(struct_to_dict(pOrder)))
        TradingAPI.update_ctp_order(pOrder)
        # super().OnRtnOrder(pOrder)

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
        data = struct_to_dict(pInvestorPosition)

        D = "L" if data['PosiDirection'] == '2' else 'S'

        position = ujson.loads(redis.hget("Position", data['InstrumentID']) or "{}")
        position[f'Total{D}Position'] = data['Position']
        position[f'Yd{D}Position'] = data['YdPosition']
        position[f'Today{D}Position'] = data['TodayPosition']
        position['NetAmount'] = position.get('TotalLPosition', 0) - position.get('TotalSPosition', 0)

        # Redis Status
        redis.hset("Position", data['InstrumentID'], ujson.dumps(position))

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        api.action("ctp_order", "partial_update", params={
            "OrderRef": pInputOrder.OrderRef.decode("gbk"),
            "Finished": True,
            "StatusMsg": pRspInfo.ErrorMsg.decode("gbk"),
            "CancelTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })

    def send_order(self, instrument, price, volume, direction, offset, order_id):
        orderref = str(self.inc_orderref_id())
        order = ApiStruct.InputOrder(
            BrokerID=self.broker_id,
            InvestorID=self.investor_id,
            InstrumentID=instrument.encode(),
            OrderRef=orderref.encode(),
            UserID=self.investor_id,
            OrderPriceType=ApiStruct.OPT_LimitPrice,
            LimitPrice=price,
            VolumeTotalOriginal=volume,
            Direction=direction.encode(),
            CombOffsetFlag=offset.encode(),
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
        TradingAPI.insert_ctp_order(self.account_name, order_id, order, self.front_id)
        return orderref

    def cancel_order(self, instrument, order_ref, front_id, session_id):
        """
        撤单
        """
        req = ApiStruct.InputOrderAction()
        req.InstrumentID = instrument.encode()
        req.OrderRef = order_ref.encode()
        req.FrontID = front_id
        req.SessionID = session_id

        req.ActionFlag = ApiStruct.AF_Delete  # 删除
        req.BrokerID = self.broker_id
        req.InvestorID = self.investor_id
        req.UserID = self.investor_id
        self.ReqOrderAction(req, self.inc_request_id())

    def query_position(self):
        req = ApiStruct.QryInvestorPosition(BrokerID=self.broker_id,
                                            InvestorID=self.investor_id)
        self.ReqQryInvestorPosition(req, self.inc_request_id())


class TaskManager:
    def __init__(self, trader: TraderBot, loop: asyncio.AbstractEventLoop=None):
        self.trader = trader
        self.loop = loop

    async def run(self):
        # 第一次先启动所有“已运行”的任务，然后只轮询“未启动”的任务
        status_flag = OrderStatus.RUNNING

        while True:
            resp = api.action("order", "list", params={"Status": status_flag, "Account": self.trader.account_name})
            for order in resp:
                self.submit(order['ID'])
            await asyncio.sleep(1, loop=self.loop)
            status_flag = OrderStatus.INACTIVE

    def submit(self, order_id):
        # 把任务状态设置为“已运行”
        api.action("order", "partial_update", params={"ID": order_id, "Status": 1})
        # 正式开始发单
        asyncio.ensure_future(self.trade(order_id), loop=self.loop)

    def get_task(self, order_id):
        task = api.action("order", "read", params={"ID": order_id})
        task['split_options'] = {
            "sleep_after_submit": task['SplitSleepAfterSubmit'],
            "sleep_after_cancel": task['SplitSleepAfterCancel'],
            "split_percent": task['SplitPercent'],
        }
        return task

    async def trade(self, order_id):
        task = self.get_task(order_id)
        if task['Status'] == OrderStatus.FINISHED:
            return
        if task['Offset'] == ApiStruct.OF_Close:
            # 处理平仓，优先平昨
            if task['Direction'] == ApiStruct.D_Buy:
                cs = 'S'
            else:
                cs = 'L'
            position = TraderInterface.query_position(task['InstrumentID'])
            # 优先使用昨仓
            volumes_holding = position.get(f'Yd{cs}Position', 0)
            offset = ApiStruct.OF_CloseYesterday
            if not volumes_holding:
                # 如果没有昨仓，使用今仓
                volumes_holding = position.get(f'Today{cs}Position', 0)
                offset = ApiStruct.OF_CloseToday
            if not volumes_holding:
                # 如果已经没有仓位了，取消整个订单
                api.action("order", "partial_update", params={
                    "ID": order_id,
                    "Status": OrderStatus.FINISHED,
                    "StatusMsg": "平仓数量不够",
                    "CancelTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                })
                return
        else:
            # 如果开仓，不限数量
            volumes_holding = 99999999999
            offset = task['Offset']
        volumes_left = min(task['VolumesTotal'] - task['VolumesTraded'], volumes_holding)
        trade_volume = self.decide_volume(volumes_left, task['split_options'])
        price = self.decide_price(task['InstrumentID'], task['Direction'], task['Price'])
        orderref = self.trader.send_order(task['InstrumentID'],
                                          price,
                                          trade_volume,
                                          task['Direction'],
                                          offset,
                                          order_id)
        await asyncio.sleep(task['split_options']['sleep_after_submit'], loop=self.loop)
        ctp_order = TradingAPI.get_ctp_order(orderref)
        if not ctp_order['Finished']:
            self.trader.cancel_order(task['InstrumentID'], orderref, self.trader.front_id, self.trader.session_id)
        if ctp_order.get('CancelTime'):
            # 如果CTP发单出错，那么直接取消整个订单
            api.action("order", "partial_update", params={
                "ID": order_id,
                "Status": OrderStatus.FINISHED,
                "StatusMsg": ctp_order['StatusMsg'],
                "CancelTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            })
            return
        await asyncio.sleep(task['split_options']['sleep_after_cancel'], loop=self.loop)
        await self.trade(order_id)

    @staticmethod
    def decide_volume(total_volume, split_options):
        percent = split_options['split_percent']
        volume = max(min(max(round(percent * total_volume), 1), total_volume), 0)
        return volume

    @staticmethod
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

    def __init__(self, account_name):
        self.account_name = account_name
        self.loop = None
        self.trader = TraderBot(account_name)
        self.trader.login()
        self.task_manager = TaskManager(self.trader)

    @staticmethod
    def query_position(instrument):
        empty_position = '{"TotalLPosition": 0, "YdLPosition": 0, "TodayLPosition": 0, "NetAmount": 0}'
        return ujson.loads(redis.hget("Position", instrument) or empty_position)

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
        if split_options is None:
            split_options = {
                "sleep_after_submit": 1,
                "sleep_after_cancel": 1,
                "split_percent": 1,
            }
        order_id = TradingAPI.insert_order(self.account_name, instrument, price, volume, direction, offset, split_options)
        # self.task_manager.submit(order_id)
        asyncio.sleep(0.01, loop=self.loop)
        return {'order_id': order_id}

    @status_monitor("TradeBot")
    async def run(self, loop):
        self.task_manager.loop = self.loop = loop
        URL = "ipc:///tmp/tradebot.sock"
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.REP)
        sock.bind(URL)
        while not self.trader.login_status:
            # 等待直到CTP登录全部完成
            await asyncio.sleep(1)
        print("CTP Login Completed")
        asyncio.ensure_future(self.task_manager.run(), loop=loop)
        loop.call_soon(self._query_ctp_position)
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

    def _query_ctp_position(self):
        """每20秒向CTP请求一次仓位"""
        self.trader.query_position()
        self.loop.call_later(20, self._query_ctp_position)


if __name__ == "__main__":
    TraderInterface('simnow').run()
