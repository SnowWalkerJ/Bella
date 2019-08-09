import asyncio
from bella.client.trader import Trader


account = "simnow"


async def test(trader: Trader):
    position = await trader.query_position("IC1908")
    print(position)
    await trader.buy("IC1908", 1)


if __name__ == "__main__":
    trader = Trader(account)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(trader))
