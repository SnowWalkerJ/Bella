from bella.common.asyncloop import ThreadSafeAsyncLoop
# from bella.common.ctp.market import Market
from bella.main.market import MarketServer


if __name__ == '__main__':
    try:
        loop = ThreadSafeAsyncLoop()
        market = MarketServer(loop) # (b'042520', b'lovefei921', b'9999')
        market.ioloop = loop
        market.Create(b'./market')
        market.RegisterFront(b'tcp://180.168.146.187:10031')
        market.Init()
        loop.run_forever()
    except KeyboardInterrupt:
        market.Release()
        loop.stop()
