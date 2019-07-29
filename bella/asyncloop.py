import asyncio


class ThreadSafeAsyncLoop(asyncio.AbstractEventLoop):
    """通过`call_soon_threadsafe`在多线程中使用异步循环"""
    def __init__(self, loop=None):
        self.__loop = loop or asyncio.get_event_loop()

    def run_forever(self):
        return self.__loop.run_forever()

    def call_soon(self, callable, *args):
        return self.__loop.call_soon_threadsafe(callable, *args)

    def call_later(self, delay, callable, *args):
        return self.__loop.call_soon_threadsafe(self.__loop.call_later, delay, callable, *args)

    def call_at(self, when, callable, *args):
        return self.__loop.call_soon_threadsafe(self.__loop.call_at, when, callable, *args)

    def call_periodic(self, interval, callable, *args):
        """每隔`interval`秒调用一次函数"""
        def fn():
            callable(*args)
            self.call_later(interval, fn)
        return self.__loop.call_soon_threadsafe(fn)

    def stop(self):
        return self.__loop.stop()

    def close(self):
        return self.__loop.close()

    @property
    def ioloop(self):
        return self.__loop
