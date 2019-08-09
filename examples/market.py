import asyncio

from bella.client.market import Market


def test_market(market: Market):
    async for data in market.subscribe_tick("IC1908"):
        print(data)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    market = Market()
    loop.run_until_complete(test_market(market))
