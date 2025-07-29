import ccxt
import ccxt.pro
import asyncio
import core.tradeManager
import core.websocketManager
from util.sLogger import logger
import os
from dotenv import load_dotenv

load_dotenv()
apiKey = os.getenv("apiKey")
secret = os.getenv("secret")
password = os.getenv("password")
sandbox = os.getenv("sandbox")
async def runWebsocketTask(symbolName:str):
    exchangeWS = ccxt.pro.bitget({
        'apiKey': apiKey,
        'secret': secret,
        'password': password,
        'options': {
            'defaultType': 'swap',
        },
        'sandbox': sandbox == "True"
    })
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

if __name__ == "__main__":
    main()