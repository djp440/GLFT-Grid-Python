import ccxt
import ccxt.pro
import asyncio
from util.sLogger import logger
import os
from dotenv import load_dotenv


async def devMode():
    exchange = ccxt.pro.bitget({
        'apiKey': os.getenv('prod_apiKey'),
        'secret': os.getenv('prod_secret'),
        'password': os.getenv('prod_password'),
        'enableRateLimit': True,
    })
    symbol = "SBTC/SUSDT:SUSDT"
    try:
        # order = await exchange.createOrder(symbol, "market", "sell", 0.01, None, {"reduceOnly": False, "hedged": True})
        # order = await exchange.fetch_closed_orders(symbol)
        position = await exchange.watch_positions([symbol], params={
            'productType': 'SUSDT-FUTURES'
        })
        logger.info(position)
        # ohlcv_data = await exchange.fetch_ohlcv(
        #     symbol=symbol,
        #     timeframe='1m',
        #     limit=20
        # )
        # logger.info(ohlcv_data)
        # logger.info(order)
    except Exception as e:
        logger.error(f"错误: {e}")
    finally:
        await exchange.close()


def main():
    load_dotenv()
    asyncio.run(devMode())


if __name__ == "__main__":
    main()
