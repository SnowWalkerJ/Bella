"""
CTP交易接口
"""
from collections import defaultdict
from decimal import Decimal
import json
import datetime
import pickle
from queue import Queue
import tempfile
import time
import logging

from ._ctp import ApiStruct, TraderApi

from .utils import struct_to_dict
from ..restful import api


logger = logging.getLogger("trader")


CTP_NOT_INITED = 7
CTP_FRONT_NOT_ACTIVE = 8


class Trader(TraderApi):
    def __init__(self, host, investor_id, broker_id, password, app_id, auth_code):
        self.host = host
        self.investor_id = investor_id
        self.broker_id = broker_id
        self.password = password
        self.app_id = app_id
        self.auth_code = auth_code

        self.connected = False
        self.login_status = False
        self.instruments = {}
        self.settlement_info = ''  
        self.investor_positions = defaultdict(dict)     # 投资者持仓
        self.__positions_cache = {}                    # 持仓缓存（持仓信息是分批发送的，先存在缓存中）

        self.session_id = ''
        self.front_id = ''
        self.request_id = 0
        self.orderref_id = int(time.time())

    ############# 主动API

    def start(self):
        tmp_path = tempfile.mkdtemp(prefix=f"trader_{datetime.date.today().strftime('%Y%m%d')}_")
        self.Create(tmp_path + "/")
        self.SubscribePrivateTopic(ApiStruct.TERT_RESUME)  # 从本交易日开始重传       
        self.SubscribePublicTopic(ApiStruct.TERT_RESUME)             
        self.RegisterFront(self.host)  # 注册前置机
        self.Init()

    def authenticate(self):
        req = ApiStruct.ReqAuthenticateField(
            BrokerID=self.broker_id,
            UserID=self.investor_id,
            AppID=self.app_id,
            AuthCode=self.auth_code,
        )
        r = self.ReqAuthenticate(req, self.inc_request_id())
        logger.info(f'ReqAuthenticate status:[{r}]')

    def login(self):
        req = ApiStruct.ReqUserLoginField(BrokerID=self.broker_id, UserID=self.investor_id, Password=self.password)
        r = self.ReqUserLogin(req, self.inc_request_id())
        logger.info(f'user login status:[{r}]')

    def getAccount(self):
        """查询资金账户"""
        req = ApiStruct.QryTradingAccountField(BrokerID=self.broker_id, InvestorID=self.investor_id, BizType=0)
        self.ReqQryTradingAccount(req, self.inc_request_id())

    def getInstrument(self):
        """查询合约"""
        req = ApiStruct.QryInstrumentField()
        logger.info('获取有效合约')
        result = self.ReqQryInstrument(req, self.inc_request_id())
        logger.debug(f'getInstrument, result:[{result}]')

    def getInvestor(self):
        """查询投资者"""
        logger.info("查询投资者")
        req = ApiStruct.QryInvestorField(BrokerID=self.broker_id, InvestorID=self.investor_id)   
        self.ReqQryInvestor(req, self.inc_request_id())

    def getPosition(self):
        """查询持仓"""
        req = ApiStruct.QryInvestorPositionField(BrokerID=self.broker_id, InvestorID=self.investor_id)                  
        result = self.ReqQryInvestorPosition(req, self.inc_request_id())
        logger.debug(f'GetPosition ,result:[{result}]')

    def getPositionDetail(self):
        """查询分笔持仓"""
        req = ApiStruct.QryInvestorPositionDetailField(BrokerID=self.broker_id, InvestorID=self.investor_id)                  
        result = self.ReqQryInvestorPositionDetail(req, self.inc_request_id())
        logger.debug(f'GetPositionDetail, result:[{result}]')

    def getSettlement(self, trading_day=''):
        self.settlement_info = ''
        trading_day = trading_day or self.trading_day

        req = ApiStruct.QrySettlementInfoField(BrokerID=self.broker_id, InvestorID=self.investor_id, TradingDay=trading_day)        
        result = self.ReqQrySettlementInfo(req, self.inc_request_id())
        logger.debug(f'获取结算单信息 {trading_day}, getSettlement {result}')

    def confirmSettlement(self):
        """
        确认结算信息
        """
        logger.info("确认结算信息")
        req = ApiStruct.SettlementInfoConfirmField(BrokerID=self.broker_id, InvestorID=self.investor_id)
        result = self.ReqSettlementInfoConfirm(req, self.inc_request_id())
        logger.debug(f"confirmSettlement [{result}]")

    ############# 前台连接

    def OnFrontConnected(self):
        """
        前置机连接成功,用户登录
        """
        self.login()

    def OnFrontDisconnected(self, nReason):
        self.connected = False
        self.need_relogin = False
        self.login_status = False
        self.instruments.clear()  # 清除合约
        logger.warn(f'OnFrontDisconnected:[{nReason}]')

    ############## 通知

    def OnRtnTrade(self, pTrade):
        """成交通知"""
        logger.info(f"OnRtnTrade {struct_to_dict(pTrade)}")

    def OnRtnOrder(self, pOrder):
        """
        报单通知（通过参数检测->已经提交成功）
        """
        # self.orderref_mapper[pOrder.OrderRef] = pOrder.CombOffsetFlag  # 记录开仓 平昨 平今标记        
        logger.info(f"OnRtnOrder {struct_to_dict(pOrder)}")

    def OnRtnInstrumentStatus(self, pInstrumentStatus):
        """合约交易状态通知"""
        # logger.info("OnRtnInstrumentStatus", struct_to_dict(pInstrumentStatus))
        pass

    def OnRtnTradingNotice(self, pTradingNoticeInfo):
        """交易通知"""
        logger.info("OnRtnTradingNotice")

    ############## 回报

    def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
        if pRspInfo.ErrorID:
            logger.error(f"Authenticate Error: {pRspInfo.ErrorMsg.decode('gbk')}")
        else:
            self.login()

    def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
        # 没有初始化,前置不活跃
        if pRspInfo.ErrorID in(CTP_NOT_INITED, CTP_FRONT_NOT_ACTIVE):
            logger.warn(f'需要释放原始连接,重新初始化连接! ErrorID: {pRspInfo.ErrorID} ')
            time.sleep(300)  # 避免过多重复无效连接
            self.need_relogin = True
        elif pRspInfo.ErrorID != 0:
            error_msg = pRspInfo.ErrorMsg.decode('gbk')
            logger.error(f'OnRspUserLogin:[ErrorID={pRspInfo.ErrorID},ErrMsg={error_msg}]')
        else:
            self.front_id = pRspUserLogin.FrontID
            self.session_id = pRspUserLogin.SessionID
            if self.session_id < 0:
                print(pRspUserLogin)
            self.trading_day = self.GetTradingDay()

            logger.info(f'{datetime.datetime.now()} {pRspUserLogin}')
            logger.info(f'GetTradingDay:[{self.trading_day}] GetApiVersion:[{self.GetApiVersion()}]')

            # 先确认投资者结算,确认后才可交易
            self.getSettlement()
            # 确认结算信息
            self.confirmSettlement()

    def OnRspError(self, pRspInfo, nRequestID, bIsLast):
        logger.error(f"OnRspError {struct_to_dict(pRspInfo)}")

    def OnRspOrderAction(self, pInputOrderAction, pRspInfo, nRequestID, bIsLast):
        """报单操作请求响应"""
        logger.error(f"OnRspOrderAction {pInputOrderAction} {struct_to_dict(pRspInfo)} {nRequestID} {bIsLast}")

    def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
        """请求查询资金账户响应"""
        logger.info(f"OnRspQryTradingAccount {pTradingAccount}, {struct_to_dict(pRspInfo)}, {nRequestID}, {bIsLast}")

    def OnRspQryInstrument(self, pInstrument, pRspInfo, nRequestID, bIsLast):
        """请求查询合约响应"""
        data = struct_to_dict(pInstrument)
        data['OptionsType'] = '0'
        data['LongMarginRatio'] = float(Decimal(data['LongMarginRatio']).quantize(Decimal('0.000')))
        data['ShortMarginRatio'] = float(Decimal(data['ShortMarginRatio']).quantize(Decimal('0.000')))
        self.instruments[pInstrument.InstrumentID.decode()] = data
        if bIsLast:
            logger.info(f"获取有效合约完成！总共 {len(self.instruments)} 个合约")
            self.connected = True
            self.need_relogin = False
            for instrument in self.instruments.values():
                try:
                    api.action("instruments", "create", params=instrument)
                except Exception:
                    pass
            with open(f"instruments_{self.trading_day}", "wb") as f:
                pickle.dump(self.instruments, f)

    def OnRspQryInvestor(self, pInvestor, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者响应"""
        logger.info(f"OnRspQryInvestor {pInvestor}, {struct_to_dict(pRspInfo)}, {nRequestID}, {bIsLast}")

    def OnRspQryInvestorPositionDetail(self, pInvestorPositionDetail, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者仓位明细响应"""
        data = struct_to_dict(pInvestorPositionDetail)
        logger.info(f"OnRspQryInvestorPositionDetail {data}")

    def OnRspQrySettlementInfo(self, pSettlementInfo, pRspInfo, nRequestID, bIsLast):
        """请求查询投资者结算结果响应"""
        if not pSettlementInfo:
            logger.info("无结算结果")
            return

        data = struct_to_dict(pSettlementInfo)

        self.settlement_info += data.get('Content')
        if bIsLast:
            filename = f"settlements/{pSettlementInfo.TradingDay.decode()}-{pSettlementInfo.InvestorID.decode()}.txt"
            with open(filename, "w") as f:
                f.write(self.settlement_info)
            logger.info('结算单信息已生成 ')

    def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
        """投资者结算结果确认响应"""
        logger.info(f'确认结算信息完成![{pSettlementInfoConfirm}]')
        time.sleep(2)  # 防止查询未就绪
        # 请求合约
        self.login_status = True
        self.getInstrument()

    ########## 错误

    def OnErrRtnOrderAction(self, pOrderAction, pRspInfo):
        """报单撤单操作错误回报"""
        logger.error(f"OnErrRtnOrderAction {struct_to_dict(pOrderAction)} {struct_to_dict(pRspInfo)}")

    def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
        """报单录入错误回报(交易所回报)"""
        logger.error(f"OnErrRtnOrderInsert {struct_to_dict(pInputOrder)} {struct_to_dict(pRspInfo)}")

    def inc_request_id(self):
        self.request_id += 1
        return self.request_id

    def inc_orderref_id(self):
        self.orderref_id += 1
        return self.orderref_id
