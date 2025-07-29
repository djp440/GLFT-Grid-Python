from pickle import NONE
import sys
from util.sLogger import logger

class TradeManager:
    def __init__(self,  symbolName: str,wsExchange,baseSpread=0.0008,minSpread=0.0005,maxSpread=0.002,orderCoolDown=0.5):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        #价差需要除以2，因为是双边应用
        self.baseSpread = baseSpread/2
        self.minSpread = minSpread/2
        self.maxSpread = maxSpread/2
        self.balance:float = None
        self.lastPrice:float = None
        self.position = []
        self.orderAmount:float = None
        #下单冷却时间
        self.orderCoolDown = orderCoolDown
        self.openOrders = []

    #创建完对象后必须调用这个函数
    async def initSymbolInfo(self):
        e = self.wsExchange
        #初始化余额
        try:
            balance = await e.fetchBalance()
            self.balance = balance['USDT']['free']
            logger.info(f"当前余额: {self.balance}")
        except Exception as e:
            logger.error(f"初始化获取余额信息失败，终止程序: {e}")
            sys.exit(1)

        #初始化交易对信息
        try:
            symbolInfo = await e.loadMarkets(self.symbolName)
            self.minOrderAmount = symbolInfo[self.symbolName]['limits']['amount']['min']
            self.pricePrecision = symbolInfo[self.symbolName]['precision']['price']
            self.amountPrecision = symbolInfo[self.symbolName]['precision']['amount']
            logger.info(f"{self.symbolName}：最小订单数量{self.minOrderAmount},价格精度{self.pricePrecision},数量精度{self.amountPrecision}")
            if self.orderAmount is not None :
                if self.orderAmount < self.minOrderAmount:
                    self.orderAmount = self.minOrderAmount
                    logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            else:
                self.orderAmount = self.minOrderAmount
                logger.warning(f"{self.symbolName}订单数量未设置，默认设置为最小订单数量{self.minOrderAmount}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化市场信息失败，终止程序: {e}")  
            sys.exit(1)

        #初始化未成交的订单信息
        try:
            allOpenOrder = await e.fetchOpenOrders(self.symbolName)
            self.openOrders = allOpenOrder
            logger.info(f"{self.symbolName}当前订单: {self.openOrders}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取订单信息失败，终止程序: {e}")
            sys.exit(1)
        
        #初始化持仓信息
        try:
            allPosition = await e.fetchPositions()
            self.position = allPosition
            logger.info(f"{self.symbolName}当前持仓: {self.position}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取持仓信息失败，终止程序: {e}")
            sys.exit(1)

        logger.info(f"{self.symbolName}初始化完成")
        

    #更新余额
    async def updateBalance(self,balance:float):
        self.balance = balance
        logger.info(f"{self.symbolName}当前余额更新为{balance}")

    #更新最新价格
    async def updateLastPrice(self,lastPrice:float):
        if self.lastPrice != lastPrice:
            logger.info(f"{self.symbolName}最新价格更新为{lastPrice}")
            self.lastPrice = lastPrice
            

    #更新持仓
    async def updatePosition(self,position):
        self.position = position
        logger.info(f"{self.symbolName}当前持仓更新: {self.position}")

    #更新订单数量
    async def updateOrderAmount(self,orderAmount:float):
        if orderAmount < self.minOrderAmount:
            logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            self.orderAmount = self.minOrderAmount
        else:
            self.orderAmount = orderAmount
