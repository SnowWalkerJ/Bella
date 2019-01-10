from datetime import timedelta
import time

import ujson
from arctic import TICK_STORE
from arctic.date import DateRange
from arctic.exceptions import OverlappingDataException
import numpy as np
import pandas as pd
from quant.utils import Logger
from startpro.core.utils.loader import safe_init_run
from startpro.core.process import Process

from bella.common.db import redis, arctic
from bella.common.tables.bar_period import BarPeriod


class Main(Process):
    name = "data_arctic_saver"

    @safe_init_run
    def run(self, **kwargs):
        Logger.info("启动data_arctic_saver")
        self.initialize_libraries()
        self.dump_ticks()
        self.dump_bars()

    def initialize_libraries(self):
        libs = arctic.list_libraries()
        if "ticks" not in libs:
            arctic.initialize_library("ticks", TICK_STORE)
        for bp in BarPeriod.objects:
            name = f"bars_{bp.period}"
            if name not in libs:
                arctic.initialize_library(name, TICK_STORE)

    def dump_ticks(self):
        keys = redis.keys("ZSET:TICK:*")
        for key in keys:
            key = key.decode()
            instrument = key.split(":")[-1]
            data = []
            for tick in redis.zrangebyscore(key, '-inf', '+inf'):
                tick = ujson.loads(tick)
                tick['Timestamp'] *= 1_000_000
                data.append(tick)
            data = pd.DataFrame(data).set_index("TickTime")
            data.index = pd.to_datetime(data.index).tz_localize("Asia/Shanghai")
            if data.index.duplicated().any():
                duplicated_index = np.where(data.index.duplicated())[0] - 1
                index = [i for i in range(data.shape[0]) if i not in duplicated_index]
                data = data.iloc[index]
            assert not data.index.duplicated().any()
            Logger.info(f"向arctic写入ticks[{instrument}]数据")
            try:
                arctic['ticks'].write(instrument, data)
            except OverlappingDataException:
                # Remove overlapping from old data
                old_data = arctic['ticks'].read(instrument)
                arctic['ticks'].delete(instrument)
                old_data = old_data.truncate(None, data.index[0] - timedelta(milliseconds=500))
                arctic['ticks'].write(instrument, old_data)
                arctic['ticks'].write(instrument, data)
            Logger.info(f"从redis中删除临时ticks[{instrument}]数据")
            redis.delete(key)

    def dump_bars(self):
        keys = redis.keys("ZSET:BAR:*")
        for key in keys:
            key = key.decode()
            freq, instrument = key.split(":")[-2:]
            data = []
            for bar in redis.zrangebyscore(key, '-inf', '+inf'):
                bar = ujson.loads(bar)
                bar['timestamp'] *= 1_000_000
                data.append(bar)
            data = pd.DataFrame(data).set_index("timestamp")
            data.index = pd.to_datetime(data.index).tz_localize("Asia/Shanghai")
            Logger.info(f"向arctic写入bars.{freq}[{instrument}]")
            try:
                arctic[f'bars_{freq}'].write(instrument, data)
            except OverlappingDataException:
                # Remove overlapping from old data
                old_data = arctic[f'bars_{freq}'].read(instrument)
                arctic[f'bars_{freq}'].delete(instrument)
                old_data = old_data.truncate(None, data.index[0] - timedelta(milliseconds=500))
                arctic[f'bars_{freq}'].write(instrument, old_data)
                arctic[f'bars_{freq}'].write(instrument, data)

            Logger.info(f"从redis中删除临时bars.{freq}[{instrument}]")
            redis.delete(key)
