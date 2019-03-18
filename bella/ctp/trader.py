"""
CTP交易接口
"""
from collections import defaultdict
import datetime
import pickle
from queue import Queue
import tempfile
import time
from quant.utils import Logger
from ._ctp import TraderApi, ApiStruct
from .utils import struct_to_dict
from ..restful import api


CTP_NOT_INITED = 7
CTP_FRONT_NOT_ACTIVE = 8


class Trader(TraderApi):
    def __init__(self, host, investor_id, broker_id, password):
        self.host               = host
        self.investor_id        = investor_id
        self.broker_id          = broker_id
        self.password           = password

        self.connected          = False
        self.login_status       = False
        self.instruments        = {}
        self.settlement_info    = ''  
        self.investor_positions = defaultdict(dict)     # 投资者持仓
        self.__positions_cache  = {}                    # 持仓缓存（持仓信息是分批发送的，先存在缓存中）

        self.session_id         = ''
        self.front_id           = ''
        self.request_id         = 0
        self.orderref_id        = int(time.time())

        self.rsp_queue          = Queue()

    ############# 主动API

    def login(self):
        tmp_path = tempfile.mkdtemp(prefix=f"trader_{datetime.date.today().strftime('%Y%m%d')}_").encode()
        self.Create(tmp_path + b"/")
        self.SubscribePrivateTopic(ApiStruct.TERT_RESUME)  # 从本交易日开始重传       
        self.SubscribePublicTopic(ApiStruct.TERT_RESUME)             
        self.RegisterFront(self.host)  # 注册前置机
        self.Init()

    def getAccount(self):
        """查询资金账户"""
        req = ApiStruct.QryTradingAccount(BrokerID=self.broker_id, InvestorID=self.investor_id)        
        self.ReqQryTradingAccount(req, self.inc_request_id())

    def getInstrument(self):
        """查询合约"""
        req = ApiStruct.QryInstrument()
        Logger.info('获取有效合约')
        result = self.ReqQryInstrument(req, self.inc_request_id())
        Logger.info(f'getInstrument, result:[{result}]')

    def getInvestor(self):
        """查询投资者"""
        Logger.info("查询投资者")
        req = ApiStruct.QryInvestor(BrokerID=self.broker_id, InvestorID=self.investor_id)   
        self.ReqQryInvestor(req, self.inc_request_id())

    def getPosition(self):
        """查询持仓"""
        req = ApiStruct.QryInvestorPosition(BrokerID=self.broker_id, InvestorID=self.investor_id)                  
        result = self.ReqQryInvestorPosition(req, self.inc_request_id())
        Logger.info(f'GetPosition ,result:[{result}]')

    def getSettlement(self, trading_day=''):
        self.settlement_info = ''
        trading_day = trading_day or self.trading_day

        req = ApiStruct.QrySettlementInfo(BrokerID=self.broker_id, InvestorID=self.investor_id, TradingDay=trading_day)        
        result = self.ReqQrySettlementInfo(req, self.inc_request_id())
        Logger.info(f'获取结算单信息 {trading_day}, getSettlement {result}')

    def confirmSettlement(self):
        """
        确认结算信息
        """
        Logger.info("确认结算信息")
        req = ApiStruct.SettlementInfoConfirm(BrokerID=self.broker_id, InvestorID=self.investor_id)
        result = self.ReqSettlementInfoConfirm(req, self.inc_request_id())
        Logger.debug(f"confirmSettlement [{result}]")

    ############# 前台连接

    def OnFrontConnected(self):
        """
        前置机连接成功,用户登录
        """
        req = ApiStruct.ReqUserLogin(BrokerID=self.broker_id, UserID=self.investor_id, Password=self.password)
        r = self.ReqUserLogin(req, self.inc_request_id())
        Logger.info(f'OnFrontConnected status:[{r}]')

    def OnFrontDisconnected(self, nReason):
        self.connected = False
        self.need_relogin = False
        self.login_status = False
        self.instruments.clear()  # 清除合约
        Logger.warn(f'OnFrontDisconnected:[{nReason}]')

    ############## 通知

    def OnRtnTrade(self, pTrade):
        """成交通知"""
        Logger.info("OnRtnTrade", pTrade)

    def OnRtnOrder(self, pOrder):
        """
        报单通知（通过参数检测->已经提交成功）
        """
        # self.orderref_mapper[pOrder.OrderRef] = pOrder.CombOffsetFlag  # 记录开仓 平昨 平今标记        
        Logger.info("OnRtnOrder", pOrder)

    def OnRtnInstrumentStatus(self, pInstrumentStatus):
        """合约交易状态通知"""
        Logger.info("OnRtnInstrumentStatus", pInstrumentStatus)
        pass

    def OnRtnTradingNotice(self, pTradingNoticeInfo):
        """交易通知"""
        Logger.info("OnRtnTradingNotice")

    ############## 回报

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        # 没有初始化,前置不活跃
        if pRspInfo.ErrorID in(CTP_NOT_INITED, CTP_FRONT_NOT_ACTIVE):
            Logger.warn(f'需要释放原始连接,重新初始化连接! ErrorID: {pRspInfo.ErrorID} ')
            time.sleep(300)  # 避免过多重复无效连接
            self.need_relogin = True
        elif pRspInfo.ErrorID != 0:
            error_msg = pRspInfo.ErrorMsg.decode('gbk')
            Logger.error(f'OnRspUserLogin:[ErrorID={pRspInfo.ErrorID},ErrMsg={error_msg}]')
        else:
            self.front_id = pRspUserLogin.FrontID
            self.session_id = pRspUserLogin.SessionID
            self.trading_day = self.GetTradingDay()

            Logger.info(f'{datetime.datetime.now()} {pRspUserLogin}')
            Logger.info(f'GetTradingDay:[{self.trading_day}] GetApiVersion:[{self.GetApiVersion()}]')

            # 先确认投资者结算,确认后才可交易
            self.confirmSettlement()

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):        
        self.rsp_queue.put((
            "OnRspError",
            {
                "pRspInfo": pRspInfo,
                "nRequestID": nRequestID,
                "bIsLast": bIsLast,
            }
        ))

    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        """报单操作请求响应"""
        Logger.error("OnRspOrderAction", pInputOrderAction, pRspInfo, nRequestID, bIsLast)

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        """请求查询资金账户响应"""
        Logger.info("OnRspQryTradingAccount", pTradingAccount, pRspInfo, nRequestID, bIsLast)

    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast):
        """请求查询合约响应"""
        data = struct_to_dict(pInstrument)
        self.instruments[pInstrument.InstrumentID.decode()] = data
        if bIsLast:
            Logger.info(f"获取有效合约完成！总共 {len(self.instruments)} 个合约")
            self.connected = True
            self.need_relogin = False
            api.action("instruments", "update", params={"data": self.instruments})
            # pickle.dump(self.instruments, open(f"instruments_{self.trading_day}", "wb"))

    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者响应"""
        Logger.info("OnRspQryInvestor", pInvestor, pRspInfo, nRequestID, bIsLast)

    def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者持仓响应"""
        if bIsLast and not pInvestorPosition and not pRspInfo:
            self.investor_position.clear()  # 空仓
            return
        pos_mapper = {'2': 'buy', '3': 'sell'}
        if pInvestorPosition.Position > 0:
            key = ":".join([pInvestorPosition.InstrumentID, pos_mapper[pInvestorPosition.PosiDirection]])
            self.__positions_cache[key] = {
                "instrument_id"        : pInvestorPosition.InstrumentID,
                "direction"            : pInvestorPosition.PosiDirection,
                "type"                 : pos_mapper[pInvestorPosition.PosiDirection],
                "position"             : pInvestorPosition.Position,
                "yd_position"          : pInvestorPosition.YdPosition,
                "today_position"       : pInvestorPosition.TodayPosition,
                "time"                 : time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "pre_settlement_price" : pInvestorPosition.PreSettlementPrice,
                "settlement_price"     : pInvestorPosition.SettlementPrice,
                "use_margin"           : pInvestorPosition.UseMargin,
                "position_profit"      : pInvestorPosition.PositionProfit,
                "trading_day"          : pInvestorPosition.TradingDay,
            }
        if bIsLast:
            self.investor_positions = self.__positions_cache.copy()

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者仓位明细响应"""
        data = struct_to_dict(pInvestorPositionDetail)
        data = json.dumps(data).decode('unicode_escape')
        Logger.info("OnRspQryInvestorPositionDetail", data, pRspInfo, bIsLast)

    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者结算结果响应"""
        if not pSettlementInfo:
            Logger.info("无结算结果")
            return

        data = struct_to_dict(pSettlementInfo)

        self.settlement_info += data.get('Content')
        data = json.dumps(data)
        if bIsLast:
            filename = "_".join(["settlement", time.strftime('%Y%m%d%H%M%S', time.localtime())])
            with open(filename, "w") as f:
                f.write(self.settlement_info)
            Logger.info('结算单信息已生成 ')

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        """投资者结算结果确认响应"""
        Logger.info(f'确认结算信息完成![{pSettlementInfoConfirm}]')
        time.sleep(2)  # 防止查询未就绪
        # 请求合约
        self.login_status = True
        self.getInstrument()

    ########## 错误

    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo):
        """报单撤单操作错误回报"""
        Logger.error('OnErrRtnOrderAction', pOrderAction, pRspInfo)

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        """报单录入错误回报(交易所回报)"""
        Logger.error("OnErrRtnOrderInsert", pInputOrder, pRspInfo)

    def inc_request_id(self):
        self.request_id += 1
        return self.request_id

    def inc_orderref_id(self):
        self.orderref_id += 1
        return self.orderref_id
