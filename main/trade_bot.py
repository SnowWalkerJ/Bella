"""
自动化交易机器人，实现拆单、对价单等高级功能
"""
import asyncio
import atexit
from datetime import datetime
import logging
import os
import sys

import ujson
import zmq
import zmq.asyncio
from coreapi.exceptions import ErrorMessage

from bella.ctp.trader import Trader
from bella.ctp.utils import struct_to_dict
from bella.ctp._ctp import ApiStruct
from bella.restful import api
from bella.config import CONFIG
from bella.db._redis import redis, create_aredis
from bella.service import status_monitor


logger = logging.getLogger("trade_bot")

logging.basicConfig(level=logging.INFO)

# TODO: 处理OnErrRtnOrderInsert
# TODO: 分离TradingAPI


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
    def get_ctp_order(sessionid, frontid, orderref):
        return api.action("ctp_order", "read", params={"session_id": sessionid, "frontid": frontid, "order_ref": orderref})

    @staticmethod
    def get_order(order_id):
        order = api.action("order", "read", params={"ID": order_id})
        order['split_options'] = {
            "sleep_after_submit": order['SplitSleepAfterSubmit'],
            "sleep_after_cancel": order['SplitSleepAfterCancel'],
            "split_percent": order['SplitPercent'],
        }
        return order

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
    def insert_ctp_order(account, order_id, pInputOrder, session_id, front_id):
        data = {
            "Account": account,
            "BrokerID": pInputOrder.BrokerID.decode(),
            "InvestorID": pInputOrder.InvestorID.decode(),
            "session_id": session_id,
            "order_ref": pInputOrder.OrderRef.decode(),
            "OrderID": order_id,
            "front_id": front_id,
            "InstrumentID": pInputOrder.InstrumentID.decode(),
            "Direction": pInputOrder.Direction.decode(),
            "Offset": pInputOrder.CombOffsetFlag.decode(),
            "Price": pInputOrder.LimitPrice,
            "VolumesTotal": pInputOrder.VolumeTotalOriginal,
            "VolumesTraded": 0,
            "InsertTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Finished": False,
        }
        api.action("ctp_order", "create", params=data)

    @staticmethod
    def insert_ctp_trade(account, pTrade):
        data = {
            "CTPOrderID": 123456,      # This is dummy
            "OrderSysID": pTrade.OrderSysID.decode(),
            "Account": account,
            "TradeID": pTrade.TradeID.decode(),
            "Price": pTrade.Price,
            "Volume": pTrade.Volume,
            "TradeTime": reformat_date(pTrade.TradeDate, pTrade.TradeTime)
        }
        api.action("ctp_trade", "create", params=data)

    @classmethod
    def update_ctp_order(cls, account_name, pOrder, session_id=None, front_id=None):
        complete_time = cancel_time = None
        if pOrder.VolumeTotal == 0:
            complete_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if pOrder.OrderStatus == ApiStruct.OST_Canceled:
            cancel_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        update_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        finished = bool(complete_time or cancel_time)
        session_id = session_id or pOrder.SessionID
        front_id = front_id or pOrder.FrontID
        data = {
            "Account": account_name,
            "BrokerID": pOrder.BrokerID.decode(),
            "InvestorID": pOrder.InvestorID.decode(),
            "session_id": session_id,
            "front_id": front_id,
            'order_ref': pOrder.OrderRef.decode(),
            "OrderSysID": pOrder.OrderSysID.decode(),
            "InstrumentID": pOrder.InstrumentID.decode(),
            "Direction": pOrder.Direction.decode(),
            "Offset": pOrder.CombOffsetFlag.decode(),
            "Price": pOrder.LimitPrice,
            "VolumesTotal": pOrder.VolumeTotalOriginal,
            'VolumesTraded': pOrder.VolumeTraded,
            'UpdateTime': update_time,
            'CompleteTime': complete_time,
            'CancelTime': cancel_time,
            'StatusMsg': pOrder.StatusMsg.decode("gbk"),
            'Finished': finished,
        }
        api.action("ctp_order", "create", params=data)

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
        print(account_info)
        self.position_detail_cache = {}
        super().__init__(account_info['TdHost'],
                         account_info['UserID'],
                         account_info['BrokerID'],
                         account_info['Password'],
                         account_info['AppID'],
                         account_info['AuthCode'],
                         )

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
        TradingAPI.update_ctp_order(self.account_name, pOrder)
        # super().OnRtnOrder(pOrder)

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        TradingAPI.update_ctp_order(self.account_name, pInputOrder, session_id=self.session_id, front_id=self.front_id)

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
        if pInvestorPosition is None:
            return
        data = struct_to_dict(pInvestorPosition)

        D = "L" if data['PosiDirection'] == '2' else 'S'

        position = ujson.loads(redis.hget("Position", data['InstrumentID']) or "{}")
        position[f'Total{D}Position'] = data['Position']
        position[f'Yd{D}Position'] = data['YdPosition']
        position[f'Today{D}Position'] = data['TodayPosition']
        position['NetAmount'] = position.get('TotalLPosition', 0) - position.get('TotalSPosition', 0)
        redis.hset(f"Position:{self.account_name}", data['InstrumentID'], ujson.dumps(position))

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        empty_position = {
            "TodayLOpen": 0,
            "TodayLClose": 0,
            "TodayLPosition": 0,
            "TodaySOpen": 0,
            "TodaySClose": 0,
            "TodaySPosition": 0,
            "YdLOpen": 0,
            "YdLClose": 0,
            "YdLPosition": 0,
            "YdSOpen": 0,
            "YdSClose": 0,
            "YdSPosition": 0,
            "TotalLPosition": 0,
            "TotalSPosition": 0,
            "NetAmount": 0,
        }
        if pInvestorPositionDetail is None:
            return
        position = self.position_detail_cache.get(pInvestorPositionDetail.InstrumentID.decode(), empty_position)
        if pInvestorPositionDetail.Direction == ApiStruct.D_Buy:
            D = 'L'
        else:
            D = 'S'
        if pInvestorPositionDetail.OpenDate == self.trading_day:
            T = 'Today'
        else:
            T = 'Yd'
        position[f'{T}{D}Close'] = position[f'{T}{D}Close'] + pInvestorPositionDetail.CloseVolume
        position[f'{T}{D}Position'] = position[f'{T}{D}Position'] + pInvestorPositionDetail.Volume
        if T == 'Today':
            position[f'{T}{D}Open'] = position[f'{T}{D}Position'] + position[f'{T}{D}Close']
        position[f'Total{D}Position'] = position[f'Today{D}Position'] + position[f'Yd{D}Position']
        position['NetAmount'] = position['TotalLPosition'] - position['TotalSPosition']
        self.position_detail_cache[pInvestorPositionDetail.InstrumentID.decode()] = position

        if bIsLast:
            for key, value in self.position_detail_cache.items():
                redis.hset(f"Position:{self.account_name}", key, ujson.dumps(value))

    ############## API

    def getPositionDetail(self):
        self.position_detail_cache = {}
        super().getPositionDetail()

    def send_order(self, instrument, price, volume, direction, offset, order_id):
        orderref = str(self.inc_orderref_id())
        order = ApiStruct.InputOrderField(
            BrokerID=self.broker_id,
            InvestorID=self.investor_id,
            InstrumentID=instrument,
            OrderRef=orderref,
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

        # 插入API必须在CTP报单之前，否则OnRtnOrder时可能查询不到报单
        TradingAPI.insert_ctp_order(self.account_name, order_id, order, self.session_id, self.front_id)

        self.ReqOrderInsert(order, self.inc_request_id())

        return self.session_id, self.front_id, orderref

    def cancel_order(self, instrument, order_ref, front_id, session_id):
        """
        撤单
        """
        req = ApiStruct.InputOrderActionField(
            InstrumentID=instrument,
            OrderRef=order_ref,
            FrontID=front_id,
            SessionID=session_id,
            ActionFlag=ApiStruct.AF_Delete,
            BrokerID=self.broker_id,
            InvestorID=self.investor_id,
            UserID=self.investor_id,
        )
        self.ReqOrderAction(req, self.inc_request_id())


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
                logger.info(f"启动任务 {order['ID']} {order['InstrumentID']} {order['Direction']} {order['VolumesTotal'] - order['VolumesTraded']} @ {order['Price']}")
                self.submit(order['ID'])
            await asyncio.sleep(1, loop=self.loop)
            status_flag = OrderStatus.INACTIVE

    def submit(self, order_id):
        # 把任务状态设置为“已运行”
        api.action("order", "partial_update", params={"ID": order_id, "Status": 1})
        # 正式开始发单
        asyncio.ensure_future(self.trade(order_id), loop=self.loop)

    def get_task(self, order_id):
        return TradingAPI.get_order(order_id)

    async def trade(self, order_id, retries=20):
        if retries == 0:
            logger.info(f"{order_id}尝试达到最大次数，停止。")
            api.action("order", "partial_update", params={
                "ID": order_id,
                "Status": OrderStatus.FINISHED,
                "StatusMsg": "尝试达到最大次数",
                "CancelTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            })
            return
        task = self.get_task(order_id)
        if task['Status'] == OrderStatus.FINISHED:
            return
        trade_volume, offset = self.decide_volume_and_offset(task)
        if not trade_volume:
            return
        price = self.decide_price(task['InstrumentID'], task['Direction'], task['Price'])
        sessionid, frontid, orderref = self.trader.send_order(task['InstrumentID'],
                                                              price,
                                                              trade_volume,
                                                              task['Direction'],
                                                              offset,
                                                              order_id)
        await asyncio.sleep(task['split_options']['sleep_after_submit'], loop=self.loop)
        ctp_order = TradingAPI.get_ctp_order(sessionid, frontid, orderref)
        if not ctp_order['Finished']:
            self.trader.cancel_order(task['InstrumentID'], orderref, frontid, sessionid)
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
        await self.trade(order_id, retries - 1)

    def decide_volume_and_offset(self, task):
        if task['Offset'] == ApiStruct.OF_Close:
            # 处理平仓，优先平昨
            if task['Direction'] == ApiStruct.D_Buy:
                cs = 'S'
            else:
                cs = 'L'
            position = TraderInterface.query_position(self.trader.account_name, task['InstrumentID'])
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
                    "ID": task['ID'],
                    "Status": OrderStatus.FINISHED,
                    "StatusMsg": "平仓数量不够",
                    "CancelTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                })
                return 0, None
        else:
            # 如果开仓，不限数量
            volumes_holding = 99999999999
            offset = task['Offset']
        volumes_left = max(min(task['VolumesTotal'] - task['VolumesTraded'], volumes_holding), 0)
        percent = task['split_options']['split_percent']
        volume = min(max(round(percent * volumes_left), 1), volumes_left)
        return volume, offset

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
        self.url = self.register(account_name)
        atexit.register(lambda: api.action("tradebot", "delete", params={"id": account_name}))
        self.loop = None
        self.trader = TraderBot(account_name)
        self.trader.start()
        self.task_manager = TaskManager(self.trader)

    def register(self, account):
        resp = api.action("tradebot", "create", params={"account": account})
        if not resp['OK']:
            raise RuntimeError(f"Tradebot with account {account} is already running")
        return resp['url']

    @staticmethod
    def query_position(account, instrument):
        position = {
            "TodayLOpen": 0,
            "TodayLClose": 0,
            "TodayLPosition": 0,
            "TodaySOpen": 0,
            "TodaySClose": 0,
            "TodaySPosition": 0,
            "YdLOpen": 0,
            "YdLClose": 0,
            "YdLPosition": 0,
            "YdSOpen": 0,
            "YdSClose": 0,
            "YdSPosition": 0,
            "TotalLPosition": 0,
            "TotalSPosition": 0,
            "NetAmount": 0,
        }
        record = redis.hget(f"Position:{account}", instrument)
        if record:
            position.update(ujson.loads(record))
        return position

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
                "sleep_after_submit": 4,
                "sleep_after_cancel": 2,
                "split_percent": 1,
            }
        order_id = TradingAPI.insert_order(self.account_name, instrument, price, volume, direction, offset, split_options)
        # self.task_manager.submit(order_id)
        return {'order_id': order_id}

    def run(self):
        status_monitor(f"Tradebot_{self.account_name}")(self._run)()

    async def _run(self, loop):
        self.task_manager.loop = self.loop = loop
        ctx = zmq.asyncio.Context()
        sock = ctx.socket(zmq.REP)
        sock.bind(self.url)
        while not self.trader.login_status:
            # 等待直到CTP登录全部完成
            await asyncio.sleep(1)
        logger.info("CTP Login Completed")
        asyncio.ensure_future(self.task_manager.run(), loop=loop)
        loop.call_soon(self._query_ctp_position)
        while 1:
            data = await sock.recv_json()
            fn_name = data['fn']
            kwargs = data['kwargs']
            logging.info(f"Incoming request: {fn_name}({kwargs})")
            if fn_name not in self.EXPOSED_METHODS:
                await sock.send(b"NotAllowed")
                continue
            fn = getattr(self, fn_name)
            result = fn(**kwargs)
            await sock.send_json(result)

    def _query_ctp_position(self):
        """每20秒向CTP请求一次仓位"""
        self.trader.getPositionDetail()
        self.loop.call_later(20, self._query_ctp_position)


if __name__ == "__main__":
    account = sys.argv[1]
    print(account)
    TraderInterface(account).run()
