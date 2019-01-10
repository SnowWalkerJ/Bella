# TODO: 在收盘后dump数据
import asyncio
from collections import defaultdict
from datetime import datetime
from aioredis.pubsub import Receiver
import ujson
from startpro.core.utils.loader import safe_init_run
from startpro.core.process import Process
from quant.utils import Logger
from bella.common.asyncloop import ThreadSafeAsyncLoop
from bella.common.constants import SECOND_UNIT, MINUTE_UNIT, HOUR_UNIT
from bella.common.db._redis import redis, create_aredis
from bella.common.exception_handler import handle_exceptions
from bella.common.service import status_monitor


PERIODS = {
    "s": (SECOND_UNIT, 0),
    "m": (MINUTE_UNIT, 0),
    "h": (HOUR_UNIT, 0),
    "d": (24 * HOUR_UNIT, 15 * HOUR_UNIT)  # 下午三点作为结算日终点
}

SUBSCRIBE_PERIODS = ["1m", "5m", "15m", "30m", "60m"]


CLOSE_PERIOD = (15, 21)


def create_bars():
    return {period: Bar(period) for period in SUBSCRIBE_PERIODS}


class Bar:
    """
    合成K线数据
    不支持夸日合成（成交量等信息会刷新）
    """
    def __init__(self, name):
        self.name = name
        self.period = self.resolve_period(name)
        self.data = {
            'pre_settlement_price': None,
            'pre_close_price'     : None,
            'pre_open_interest'   : None,
            'open_interest'       : None,
            'open'                : None,
            'close'               : None,
            'high'                : None,
            'low'                 : None,
            'start_volume'        : None,
            'end_volume'          : None,
            'timestamp'           : 0,
        }
        self.last_volume = 0
        self.is_new = True

    def resolve_period(self, name):
        unit = name[-1]
        num = int(name[:-1])
        length, remainder = PERIODS.get(unit, (1, 0))
        num = num * length
        return num, remainder

    def new(self):
        self.data = {
            'pre_settlement_price': None,
            'pre_close_price'     : None,
            'pre_open_interest'   : None,
            'open_interest'       : None,
            'open'                : None,
            'close'               : None,
            'high'                : None,
            'low'                 : None,
            'start_volume'        : None,
            'end_volume'          : None,
            'timestamp'           : None,
        }
        self.is_new = True

    @handle_exceptions(ignore=True)
    def push(self, tick):
        timestamp = tick['Timestamp']
        t1 = (timestamp - self.period[1]) // self.period[0]
        t2 = (self.data['timestamp'] - self.period[1]) // self.period[0]
        if t1 != t2 and not self.is_new:
            self.dump()
        if self.is_new:
            self.instrument = tick['InstrumentID']
            self.data.update({
                'pre_settlement_price': tick['PreSettlementPrice'],
                'pre_close_price':      tick['PreClosePrice'],
                'pre_open_interest':    tick['PreOpenInterest'],
                'open_interest':        tick['OpenInterest'],
                'open':                 tick['LastPrice'],
                'close':                tick['LastPrice'],
                'high':                 tick['LastPrice'],
                'low':                  tick['LastPrice'],
                'start_volume':         min(self.last_volume, tick['Volume']) or tick['Volume'],  # 考虑跨交割日的问题
                'end_volume':           tick['Volume'],
                'timestamp':            timestamp
            })
            self.is_new = False
        else:
            self.data['close']         = tick['LastPrice']
            self.data['high']          = max(self.data['high'], tick['LastPrice'])
            self.data['low']           = min(self.data['low'], tick['LastPrice'])
            self.data['end_volume']    = tick['Volume']
            self.data['timestamp']     = timestamp
            self.data['open_interest'] = tick['OpenInterest']
        self.last_volume = tick['Volume']

    @handle_exceptions(ignore=True)
    def dump(self):
        if CLOSE_PERIOD[0] <= self.data['timestamp'] % HOUR_UNIT < CLOSE_PERIOD[1]:
            return
        # 把时间戳对齐到整数
        remainder = self.period[0] - (self.data['timestamp'] - self.period[1]) % self.period[0]
        bar = {
            'pre_settlement_price': self.data['pre_settlement_price'],
            'pre_close_price':      self.data['pre_close_price'],
            'pre_open_interest':    self.data['pre_open_interest'],
            'open_interest':        self.data['open_interest'],
            'open':                 self.data['open'],
            'close':                self.data['close'],
            'high':                 self.data['high'],
            'low':                  self.data['low'],
            'volume':               self.data['end_volume'] - self.data['start_volume'],
            'timestamp':            self.data['timestamp'] + remainder
        }
        redis.publish(f"BAR:{self.name}:{self.instrument}", ujson.dumps(bar))
        Logger.info(f"dump {self.name} {self.instrument} @ {bar['timestamp']}")
        self.new()


class BarComposer(Process):
    name = "bar"

    def __init__(self):
        self.bars = defaultdict(create_bars)

    @handle_exceptions(ignore=True)
    def handle_tick(self, data):
        instrument = data['InstrumentID']
        for bar in self.bars[instrument].values():
            bar.push(data)

    @safe_init_run
    @status_monitor("bar")
    async def run(self, **kwargs):
        aredis = await create_aredis()
        mpsc = Receiver()
        pattern = mpsc.pattern("TICK:*")
        await aredis.psubscribe(pattern)
        Logger.info("subscribed")
        async for channel, data in mpsc.iter():
            data = ujson.loads(data[1])
            self.handle_tick(data)
