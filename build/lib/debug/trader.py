from bella.common.asyncloop import ThreadSafeAsyncLoop
from bella.common.ctp.trader import Trader


host = b"tcp://180.168.146.187:10000"
broker_id = b"9999"
investor_id = b'042520'
password = b"lovefei921"

trader = Trader(host, investor_id, broker_id, password)
trader.login()
loop = ThreadSafeAsyncLoop()
try:
    loop.run_forever()
finally:
    trader.Release()
