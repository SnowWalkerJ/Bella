import time

import ujson
from arctic import TICK_STORE
import pandas as pd
from quant.utils import Logger
from startpro.core.utils.loader import safe_init_run
from startpro.core.process import Process

from bella.common.db import redis, arctic
from bella.common.db._mongo.tables.bar_period import BarPeriod


class Main(Process):
    name = "data_arctic_saver"

    @safe_init_run
    def run(self, **kwargs):
        Logger.info("启动data_arctic_saver @", time.time())
        self.initialize_libraries()
        self.dump_ticks()
        self.dump_bars()

    def initialize_libraries(self):
        libs = arctic.list_libraries()
        if "ticks" not in libs:
            arctic.initialize_library("ticks", TICK_STORE)
        for bp in BarPeriod.objects:
            name = f"bars.{bp.Period}"
            if name not in libs:
                arctic.initialize_library(name, TICK_STORE)

    def dump_ticks(self):
        keys = redis.keys("ZSET:TICK:*")
        for key in keys:
            instrument = key.split(":")[-1]
            data = []
            for tick in redis.zrangebyscore(key, '-inf', '+inf'):
                tick = ujson.loads(tick)
                tick['Timestamp'] *= 1_000_000
                data.append(tick)
            data = pd.DataFrame(tick).set_index("TickTime")
            data.index = pd.to_datetime(data.index).tz_localize("Asia/Shanghai")
            arctic['ticks'].write(instrument, data)
            Logger.info(f"向arctic写入ticks[{instrument}]数据")
            redis.delete(key)
            Logger.info(f"从redis中删除临时ticks[{instrument}]数据")

    def dump_bars(self):
        keys = redis.keys("ZSET:BAR:*")
        for key in keys:
            freq, instrument = key.split(":")[-2:]
            data = []
            for tick in redis.zrangebyscore(key, '-inf', '+inf'):
                tick = ujson.loads(tick)
                tick['timestamp'] *= 1_000_000
                data.append(tick)
            data = pd.DataFrame(tick).set_index("timestamp")
            data.index = pd.to_datetime(data.index).tz_localize("Asia/Shanghai")
            arctic[f'bars.{freq}'].write(instrument, data)
            Logger.info(f"向arctic写入bars.{freq}[{instrument}]")
            redis.delete(key)
            Logger.info(f"从redis中删除临时bars.{freq}[{instrument}]")
