from util import tradeUtil
from util.sLogger import logger
import ccxt
import asyncio
from core.tradeManager import TradeManager


class WebSocketManager:
    def __init__(self,symbolName:str, wsExchange,tradeManage:TradeManager,run=True):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        self.tradeManager = tradeManage
        self.run = run

    async def watchTicker(self):
        logger.info(f"执行{self.symbolName}价格获取")
        while self.run:
            try:
                ticker = await self.wsExchange.watchTicker(self.symbolName)
                 # logger.info(f"{self.symbolName}当前价格: {ticker['last']}")
                await self.tradeManager.updateLastPrice(float(ticker['last']))
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}价格获取网络错误: {e}")
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}价格获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}价格获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"{self.symbolName}价格获取未知错误: {e}") 

    async def watchMyPosition(self):
      logger.info(f"执行{self.symbolName}持仓获取")
      while self.run:
        try:
            position = await self.wsExchange.watchPositions() 
            #   logger.info(f"{self.symbolName}当前持仓: {position}")
            await self.tradeManager.updatePosition(position)    
        except ccxt.NetworkError as e:  
            logger.error(f"{self.symbolName}持仓获取网络错误: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"{self.symbolName}持仓获取交易所错误: {e}")  
        except asyncio.CancelledError:
            logger.info(f"{self.symbolName}持仓获取任务已取消")
            self.run = False
        except Exception as e:
            logger.error(f"{self.symbolName}持仓获取未知错误: {e}") 

    async def watchMyBalance(self):
      logger.info(f"执行余额获取")
      while self.run:
        try:
            balance = await self.wsExchange.watchBalance()
            #   logger.info(f"当前余额: {balance['USDT']['free']}")
            await self.tradeManager.updateBalance(float(balance['USDT']['free']))
        except ccxt.NetworkError as e:
            logger.error(f"余额获取网络错误: {e}")
        except ccxt.ExchangeError as e:
            logger.error(f"余额获取交易所错误: {e}")
        except asyncio.CancelledError:
            logger.info(f"余额获取任务已取消")
            self.run = False
        except Exception as e:
            logger.error(f"余额获取未知错误: {e}") 

    async def watchMyOrder(self):
        self.wsExchange.newUpdates = False
        logger.info(f"执行{self.symbolName}订单获取")
        while self.run:
            try:
                allOrder = await self.wsExchange.watchOrders()
                targetOrder = tradeUtil.openOrderFilter(allOrder,self.symbolName)
                # logger.info(f"{self.symbolName}当前订单: {targetOrder}")
                await self.tradeManager.updateOrders(targetOrder)
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}订单获取网络错误: {e}")
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}订单获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}订单获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"{self.symbolName}订单获取未知错误: {e}")
