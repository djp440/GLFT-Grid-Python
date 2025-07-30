from decimal import Decimal
from logging import info
from pdb import run
from pickle import NONE
import sys
from turtle import update
from util.sLogger import logger
from util import tradeUtil
import asyncio

class TradeManager:
    def __init__(self,  symbolName: str,wsExchange,baseSpread=0.0008,minSpread=0.0004,maxSpread=0.002,orderCoolDown=0.1,maxStockRadio=0.25):
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
        #最大持仓比例
        self.maxStockRadio = maxStockRadio
        self.nowStockRadio = 0.0
        self.lastBuyPrice = 0.0

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
            pricePrecision = symbolInfo[self.symbolName]['precision']['price']
            amountPrecision = symbolInfo[self.symbolName]['precision']['amount']
            #计算价格、下单数量的小数位数
            self.pricePrecision = abs(Decimal(str(pricePrecision)).as_tuple().exponent)
            self.amountPrecision = abs(Decimal(str(amountPrecision)).as_tuple().exponent)
            logger.info(f"{self.symbolName}：最小订单数量{self.minOrderAmount},价格精度小数位数{self.pricePrecision},数量精度小数位数{self.amountPrecision}")
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

        # #获取交易对价格
        # try:
        #     ticker = await e.fetchTicker(self.symbolName)
        #     self.lastPrice = float(ticker['last'])
        #     logger.info(f"{self.symbolName}当前价格: {self.lastPrice}")
        # except Exception as e:
        #     logger.error(f"{self.symbolName}获取交易对价格失败，终止程序: {e}")
        #     sys.exit(1)

        # #初始化未成交的订单信息
        # try:
        #     allOrder = await e.fetchOpenOrders()
        #     openOrder = tradeUtil.openOrderFilter(allOrder,self.symbolName)
        #     self.openOrders = openOrder
        #     logger.info(f"{self.symbolName}当前订单: {self.openOrders}")
        # except Exception as e:
        #     logger.error(f"{self.symbolName}初始化获取订单信息失败，终止程序: {e}")
        #     sys.exit(1)
        
        # #初始化持仓信息
        # try:
        #     allPosition = await e.fetchPositions()
        #     self.position = allPosition
        #     logger.info(f"{self.symbolName}当前持仓: {self.position}")
        # except Exception as e:
        #     logger.error(f"{self.symbolName}初始化获取持仓信息失败，终止程序: {e}")
        #     sys.exit(1)
        
        # logger.info(f"{self.symbolName}初始化完成")
        # await self.updateStockRadio()
        # await self.runTrade()
        

    #更新余额
    async def updateBalance(self,balance:float):
        self.balance = balance
        # logger.info(f"{self.symbolName}当前余额更新为{balance}")

    #更新最新价格
    async def updateLastPrice(self,lastPrice:float):
        if self.lastPrice != lastPrice:
            # logger.info(f"{self.symbolName}最新价格更新为{lastPrice}")
            self.lastPrice = lastPrice
        #当价格超过最新买单价一定范围后重新挂买单
        if self.lastBuyPrice != 0.0:
            if lastPrice > self.lastBuyPrice * (1+self.baseSpread):
                logger.info(f"{self.symbolName}最新价格{lastPrice}超过最新买单价{self.lastBuyPrice}*(1+{self.baseSpread})，重新挂买单")
                await self.cancelAllOrder()
                await self.runTrade()
            

    #更新持仓
    async def updatePosition(self,position):
        self.position = position
        # logger.info(f"{self.symbolName}当前持仓更新: {self.position}")
        # tempRatio = self.nowStockRadio
        await self.updateStockRadio()

    #更新下单数量
    async def updateOrderAmount(self,orderAmount:float):
        if orderAmount < self.minOrderAmount:
            logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            self.orderAmount = self.minOrderAmount
        else:
            self.orderAmount = orderAmount

    #更新未成交订单
    async def updateOrders(self,orders):
        self.openOrders = orders
        # logger.info(f"{self.symbolName}未成交订单更新: {self.openOrders}")
        # logger.info(f"{self.symbolName}未成交订单数量: {len(self.openOrders)}")


    #计算下单数量
    async def calculateOrderAmount(self):
        #计算当前持仓占比占最大持仓占比的比例
        ratio = self.nowStockRadio/self.maxStockRadio
        #计算买单数量，买单数量与ratio成反比

    #计算买卖单价格
    async def calculateOrderPrice(self):
        #根据库存数量重构价差
        ratio = self.nowStockRadio/self.maxStockRadio
        buySpread,sellSpread = self.baseSpread
        balanceRatio = 0.5
        '''
        对于买单价差
        - 当 ratio = 0 时, spread = minSpread
        - 当 0 < ratio <= 0.5 时, spread 从 minSpread 线性增长到 baseSpread
        - 当 0.5 < ratio <= 1 时, spread 从 baseSpread 线性增长到 maxSpread
        '''
        if ratio < balanceRatio:
            buySpread = 2 * (self.baseSpread-self.minSpread) * (ratio - 0) + self.minSpread
            sellSpread = 2 * (self.baseSpread-self.maxSpread) * (ratio - 0) + self.maxSpread
        else:
            buySpread = 2 * (self.maxSpread-self.baseSpread) * (ratio- balanceRatio) + self.baseSpread
            sellSpread = 2 * (self.minSpread-self.baseSpread) * (ratio- balanceRatio) + self.baseSpread
        
        if buySpread < self.minSpread:
            buySpread = self.minSpread
        if buySpread > self.maxSpread:
            buySpread = self.maxSpread
        if sellSpread < self.minSpread:
            sellSpread = self.minSpread
        if sellSpread > self.maxSpread:
            sellSpread = self.maxSpread
        print(f"默认价差为{self.baseSpread}，当前持仓比例为{ratio}，当前买单价差为{buySpread}，当前卖单价差为{sellSpread}")
        #计算买卖价格
        buyPrice = self.lastPrice * (1 - buySpread)
        sellPrice = self.lastPrice * (1 + sellSpread)
        return buyPrice,sellPrice

    #更新持仓比例
    async def updateStockRadio(self):
        marginSize = tradeUtil.positionMarginSize(self.position,self.symbolName)
        ratio = marginSize / (self.balance+marginSize)
        if self.nowStockRadio != ratio:
            self.nowStockRadio = ratio
            # logger.info(f"{self.symbolName}当前持仓比例更新: {self.nowStockRadio}")
            #当持仓比例更新时，取消所有订单并重新挂单
            logger.info(f"{self.symbolName}当前持仓比例更新为{ratio}，取消所有订单并重新挂单")
            await self.cancelAllOrder()
            await self.runTrade()

    #下单
    async def placeOrder(self,amount,price,side,reduceOnly):
        amount = round(amount,self.amountPrecision)
        price = round(price,self.pricePrecision)
        if amount < self.minOrderAmount:
            logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            amount = self.minOrderAmount
        # logger.info(f"{self.symbolName}下单数量: {amount},下单价格: {price}")
        try:
            order = await self.wsExchange.createOrder(self.symbolName, "limit",side,amount, price,{"reduceOnly":reduceOnly})
        except Exception as e:
            logger.error(f"{self.symbolName}下单失败: {e}")
            return None
        else:
            logger.info(f"{self.symbolName}下单成功: {order['id']},下单数量: {amount},下单价格: {price},方向: {side}")
            if side == "buy":
                self.lastBuyPrice = self.lastPrice
            return order

    #取消全部订单
    async def cancelAllOrder(self):
        try:
            await self.wsExchange.cancelAllOrders(self.symbolName)
        except Exception as e:
            logger.error(f"{self.symbolName}取消全部订单失败: {e}")
            return False
        else:
            logger.info(f"{self.symbolName}取消全部订单成功")
            return True

    #运行流程
    async def runTrade(self):
        if tradeUtil.checkOpenOrder(self.openOrders):
            logger.info(f"{self.symbolName}当前未成交订单数量为2，且1个买单和1个卖单，跳过挂单")
            return
        
        # if len(self.openOrders) != 0:
        #     logger.info(f"{self.symbolName}当前未成交订单数量不是2，或不是1个买单和1个卖单，继续挂单")
        #     try:
        #         await self.cancelAllOrder()
        #     except Exception as e:
        #         logger.error(f"{self.symbolName}取消全部订单失败: {e}")

        try:
            buyPrice,sellPrice = await self.calculateOrderPrice()
            orderBuy = self.placeOrder(self.orderAmount,buyPrice,"buy",False)
            if self.nowStockRadio != 0:
                orderSell = self.placeOrder(self.orderAmount,sellPrice,"sell",True)
                await asyncio.gather(orderBuy,orderSell)
            else:
                await orderBuy
        except Exception as e:
            logger.error(f"{self.symbolName}下单失败: {e}")

    