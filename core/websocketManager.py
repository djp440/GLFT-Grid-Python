from util.sLogger import logger
import ccxt
import asyncio
from core.tradeManager import TradeManager

class WebSocketManager:
    def __init__(self,symbolName:str, wsExchange,tradeManage:TradeManager,watchColdDown=0.5):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        self.tradeManager = tradeManage
        self.watchColdDown = watchColdDown

    async def watchTicker(self):
        logger.info(f"执行{self.symbolName}价格获取")
        try:
            while True:
                ticker = await self.wsExchange.watchTicker(self.symbolName)
                # logger.info(f"{self.symbolName}当前价格: {ticker['last']}")
                await self.tradeManager.updateLastPrice(float(ticker['last']))
                await asyncio.sleep(self.watchColdDown)
        except ccxt.NetworkError as e:
            logger.error(f"{self.symbolName}价格获取网络错误: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"{self.symbolName}价格获取交易所错误: {e}")
        except asyncio.CancelledError:
            logger.info(f"{self.symbolName}价格获取任务已取消")
        except Exception as e:
            logger.error(f"{self.symbolName}价格获取未知错误: {e}") 

    async def watchMyPosition(self):
      logger.info(f"执行{self.symbolName}持仓获取")
      try:
          while True:
                position = await self.wsExchange.watchPositions() 
            #   logger.info(f"{self.symbolName}当前持仓: {position}")
                await self.tradeManager.updatePosition(position)    
                await asyncio.sleep(self.watchColdDown)
      except ccxt.NetworkError as e:  
          logger.error(f"{self.symbolName}持仓获取网络错误: {e}")
      except ccxt.ExchangeError as e:
          logger.error(f"{self.symbolName}持仓获取交易所错误: {e}")  
      except asyncio.CancelledError:
          logger.info(f"{self.symbolName}持仓获取任务已取消")
      except Exception as e:
          logger.error(f"{self.symbolName}持仓获取未知错误: {e}") 

    async def watchMyBalance(self):
      logger.info(f"执行余额获取")
      try:
          while True:
                balance = await self.wsExchange.watchBalance()
            #   logger.info(f"当前余额: {balance['USDT']['free']}")
                await self.tradeManager.updateBalance(float(balance['USDT']['free']))
                await asyncio.sleep(self.watchColdDown)
      except ccxt.NetworkError as e:
          logger.error(f"余额获取网络错误: {e}")
      except ccxt.ExchangeError as e:
          logger.error(f"余额获取交易所错误: {e}")
      except asyncio.CancelledError:
          logger.info(f"余额获取任务已取消")
      except Exception as e:
          logger.error(f"余额获取未知错误: {e}") 

    '''
    订单格式
    [
  {
    "info": {
      "accBaseVolume": "0",
      "cTime": "1753763423619",
      "cancelReason": "",
      "clientOid": "1333945970739740672",
      "enterPointSource": "WEB",
      "feeDetail": [
        {
          "feeCoin": "USDT",
          "fee": "0.00000000"
        }
      ],
      "force": "gtc",
      "instId": "ETHUSDT",
      "leverage": "5",
      "marginCoin": "USDT",
      "marginMode": "crossed",
      "notionalUsd": "2220",
      "orderId": "1333945970718769153",
      "orderType": "limit",
      "posMode": "one_way_mode",
      "posSide": "net",
      "presetStopLossExecutePrice": "",
      "presetStopLossType": "",
      "presetStopSurplusExecutePrice": "",
      "presetStopSurplusType": "",
      "price": "3000",
      "reduceOnly": "no",
      "side": "buy",
      "size": "0.74",
      "status": "live",
      "stpMode": "none",
      "totalProfits": "0",
      "tradeSide": "buy_single",
      "uTime": "1753763423619"
    },
    "symbol": "ETH/USDT:USDT",
    "id": "1333945970718769153",
    "clientOrderId": "1333945970739740672",
    "timestamp": 1753763423619,
    "datetime": "2025-07-29T04:30:23.619Z",
    "lastTradeTimestamp": 1753763423619,
    "type": "limit",
    "timeInForce": "GTC",
    "postOnly": false,
    "side": "buy",
    "price": 3000.0,
    "triggerPrice": null,
    "amount": 0.74,
    "cost": 0.0,
    "average": null,
    "filled": 0.0,
    "remaining": 0.74,
    "status": "open",
    "fee": {
      "cost": 0.0,
      "currency": "USDT"
    },
    "trades": [],
    "fees": [
      {
        "cost": 0.0,
        "currency": "USDT"
      }
    ],
    "lastUpdateTimestamp": null,
    "reduceOnly": null,
    "stopPrice": null,
    "takeProfitPrice": null,
    "stopLossPrice": null
  }
]
    '''
    async def watchMyOrder(self):
        self.wsExchange.newUpdates = False
        logger.info(f"执行{self.symbolName}订单获取")
        try:
            while True:
                allOrder = await self.wsExchange.watchOrders()
                logger.info(f"{self.symbolName}当前订单: {allOrder}")
                await asyncio.sleep(self.watchColdDown)
        except ccxt.NetworkError as e:
            logger.error(f"{self.symbolName}订单获取网络错误: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"{self.symbolName}订单获取交易所错误: {e}")
        except asyncio.CancelledError:
            logger.info(f"{self.symbolName}订单获取任务已取消")
        except Exception as e:
            logger.error(f"{self.symbolName}订单获取未知错误: {e}") 
