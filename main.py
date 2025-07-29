import ccxt
import ccxt.pro
import asyncio
import core.tradeManager
import core.websocketManager
from util.sLogger import logger

async def runWebsocketTask(symbolName:str):
    exchangeWS = ccxt.pro.bitget({
        'apiKey': 'bg_fbd1578819f5691740f2bec26cee2546',
        'secret': '1d92c9b226cff59250fb97972f1695c69bc4f89d39967f462403d5bc67c73cb5',
        'password': '1234abcd',
        'options': {
            'defaultType': 'swap',
        },
        'sandbox': True
    })
    # symbolInfo = await exchangeWS.loadMarkets(symbolName)
    # print(symbolInfo[symbolName])
    tm = core.tradeManager.TradeManager(symbolName,exchangeWS)
    await tm.initSymbolInfo()
    wm = core.websocketManager.WebSocketManager(symbolName,exchangeWS,tm)
    taskWatchTick = wm.watchTicker()
    taskWatchBalance = wm.watchMyBalance()  
    taskWatchPosition = wm.watchMyPosition()
    taskWatchOrder = wm.watchMyOrder()
    await asyncio.gather(taskWatchTick,taskWatchBalance,taskWatchPosition,taskWatchOrder)

def main():
    try:
        asyncio.run(runWebsocketTask("ETH/USDT:USDT"))
    except KeyboardInterrupt:
        logger.error("程序已手动中断")
    except Exception as e:
        logger.error(f"未知错误: {e}")



    # baseSpread = 0.0008/2 #基础价差，0.001代表0.1%
    # minSpread = 0.0004/2 #最小价差，0.001代表0.1%
    # markets = exchangeREST.load_markets()
    # allTickers = exchangeREST.fetch_tickers()
    # balance = exchangeREST.fetch_balance()
    # balanceUSDT = float(balance["info"][0]["crossedMaxAvailable"])
    # myMarkets = {}
    # positions = exchangeREST.fetch_positions()
    # print(f"当前持仓: {positions}")
    # ethItem = markets["ETH/USDT:USDT"]
    # ethTicker = allTickers["ETH/USDT:USDT"]
    # ethPrice = float(ethTicker['last'])
    # buyPrice = ethPrice * (1 - baseSpread)
    # sellPrice = ethPrice * (1 + baseSpread)
    # ethMinQty = float(ethItem["limits"]["amount"]["min"])

if __name__ == "__main__":
    main()