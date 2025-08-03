from decimal import Decimal
import sys
from turtle import up
from util.sLogger import logger
from util import tradeUtil
import asyncio
from core.dataRecorder import data_recorder

class TradeManager:
    def __init__(self,  symbolName: str,wsExchange,baseSpread=0.001,minSpread=0.0008,maxSpread=0.003,orderCoolDown=0.1,maxStockRadio=0.25,orderAmountRatio=0.05,coin='USDT'):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        #价差需要除以2，因为是双边应用
        self.baseSpread = baseSpread/2
        self.minSpread = minSpread/2
        self.maxSpread = maxSpread/2
        self.balance:float = None
        self.equity:float = None
        self.lastPrice:float = None
        self.position = []
        self.orderAmount:float = None
        self.orderAmountRatio = orderAmountRatio
        #下单冷却时间
        self.orderCoolDown = orderCoolDown
        self.openOrders = []
        #最大持仓比例
        self.maxStockRadio = maxStockRadio
        self.nowStockRadio = 0.0
        self.lastBuyPrice = 0.0
        self.lastBuyOrderId = None
        self.lastSellOrderId = None
        self.checkOrder = False
        self._update_lock = asyncio.Lock()  # 添加锁
        self.networkError = False
        self.websocketManager = None
        self.coin = coin
    
    #创建完对象后必须调用这个函数
    async def initSymbolInfo(self):
        e = self.wsExchange
        #初始化余额
        try:
            balance = await e.fetchBalance()
            logger.info(f"{self.symbolName}当前余额: {balance}")
            await self.updateBalance(balance[self.coin]['free'],balance[self.coin]['total'])
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

        #获取交易对价格
        try:
            ticker = await e.fetchTicker(self.symbolName)
            self.lastPrice = float(ticker['last'])
            logger.info(f"{self.symbolName}当前价格: {self.lastPrice}")
        except Exception as e:
            logger.error(f"{self.symbolName}获取交易对价格失败，终止程序: {e}")
            sys.exit(1)

        #初始化未成交的订单信息
        try:
            allOrder = await e.fetchOpenOrders()
            openOrder = await tradeUtil.openOrderFilter(allOrder,self.symbolName)
            self.openOrders = openOrder
            # logger.info(f"{self.symbolName}当前订单: {self.openOrders}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取订单信息失败，终止程序: {e}")
            sys.exit(1)
        
        #初始化持仓信息
        try:
            allPosition = await e.fetchPositions()
            await self.updatePosition(allPosition)
            # logger.info(f"{self.symbolName}当前持仓: {self.position}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取持仓信息失败，终止程序: {e}")
            sys.exit(1)

        await self.updateOrderAmount()
        
        logger.info(f"{self.symbolName}初始化完成")
 
        
        
    async def bindWebsocketManager(self,websocketManager):
        self.websocketManager = websocketManager
    
    async def onOrderFilled(self, filled_orders=None):
        """
        处理订单成交后的逻辑
        """
        if filled_orders is None:
            filled_orders = []
        
        logger.info(f"{self.symbolName}处理订单成交事件，成交订单数量: {len(filled_orders)}")

        # 记录成交订单数据
        try:
            for order in filled_orders:
                if order and 'filled' in order and order['filled'] > 0:
                    # 计算手续费（如果订单中没有手续费信息，使用估算值）
                    fee = order.get('fee', {}).get('cost', 0)
                    if fee == 0 and 'cost' in order:
                        # 估算手续费为成交金额的0.1%
                        fee = order['cost'] * 0.001
                    
                    await data_recorder.record_trade(
                        symbol=self.symbolName,
                        side=order['side'],
                        amount=order['filled'],
                        price=order['average'] or order['price'],
                        fee=fee,
                        order_id=order['id']
                    )
        except Exception as e:
            logger.error(f"{self.symbolName}记录交易数据时发生错误: {e}")

        # 更新订单状态和持仓信息
        try:
            # 重新获取最新的订单信息
            allOrder = await self.wsExchange.fetchOpenOrders(self.symbolName)
            targetOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)
            await self.updateOrders(targetOrder)
            
            # 重新获取持仓信息
            allPosition = await self.wsExchange.fetchPositions()
            await self.updatePosition(allPosition)
            
            # 重新获取余额信息
            balance = await self.wsExchange.fetchBalance()
            await self.updateBalance(balance[self.coin]['free'],balance[self.coin]['total'])
            
            logger.info(f"{self.symbolName}订单成交后状态更新完成")
            
            # 延迟一段时间后重新挂单，避免频繁操作
            await asyncio.sleep(self.orderCoolDown)
            
            # 重新执行交易逻辑
            await self.runTrade()
            
        except Exception as e:
            logger.error(f"{self.symbolName}处理订单成交事件时发生错误: {e}")
            # 如果出错，尝试网络重连
            await self.networkHelper()

    # 检查和恢复订单监听状态
    async def checkAndRecoverOrderWatch(self):
        """
        检查订单监听状态并在需要时恢复
        """
        try:
            if self.websocketManager:
                # 检查是否有活跃的订单监听
                if not await self.websocketManager.isOrderWatchActive():
                    logger.warning(f"{self.symbolName}订单监听已断开，尝试恢复")
                    # 获取当前未成交订单
                    allOrder = await self.wsExchange.fetchOpenOrders(self.symbolName)
                    targetOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)
                    
                    if len(targetOrder) > 0:
                        # 重新启动订单监听
                        if len(targetOrder) == 2:
                            await self.websocketManager.runOpenOrderWatch(targetOrder[0], targetOrder[1])
                        else:
                            await self.websocketManager.runOpenOrderWatch(targetOrder[0])
                        logger.info(f"{self.symbolName}订单监听恢复成功")
                    else:
                        logger.info(f"{self.symbolName}当前无未成交订单，无需恢复监听")
                        # 重新执行交易逻辑以创建新订单
                        await self.runTrade()
        except Exception as e:
            logger.error(f"{self.symbolName}检查和恢复订单监听时发生错误: {e}")
            # 如果恢复失败，触发网络重连
            await self.networkHelper()

    #更新余额
    async def updateBalance(self,balance:float,equity:float):
        self.balance = balance
        self.equity = equity
        logger.info(f"{self.symbolName}当前余额: {self.balance},当前权益: {self.equity}")
        
        # 更新数据记录器中的权益信息
        try:
            await data_recorder.update_equity(equity)
        except Exception as e:
            logger.error(f"{self.symbolName}更新权益数据时发生错误: {e}")

    #更新最新价格
    async def updateLastPrice(self,lastPrice:float):
        if self.lastPrice != lastPrice:
            self.lastPrice = lastPrice
        #当没有持仓且价格超过最新买单价一定范围后重新挂买单
        if self.lastBuyPrice != 0.0:
            # 当没有持仓且价格超过最新买单价一定范围时重新挂买单
            if await tradeUtil.positionMarginSize(self.position,self.symbolName) == 0 and lastPrice > self.lastBuyPrice * (1 + self.baseSpread):
                logger.info(f"{self.symbolName}无持仓且最新价格{lastPrice}超过最新买单价{self.lastBuyPrice}*(1+{self.baseSpread})，重新挂买单")
                await self.runTrade()
        
        # 定期检查订单监听状态（每100次价格更新检查一次）
        if not hasattr(self, '_price_update_counter'):
            self._price_update_counter = 0
        self._price_update_counter += 1
        
        if self._price_update_counter % 100 == 0:
            await self.checkAndRecoverOrderWatch()
            

    #更新持仓
    async def updatePosition(self,position):
        self.position = position
        marginSize = await tradeUtil.positionMarginSize(self.position,self.symbolName)
        
        # 添加边界检查防止除零错误
        total_value = self.balance + marginSize
        if total_value <= 0:
            logger.warning(f"{self.symbolName}总资产为0或负数(余额:{self.balance}, 保证金:{marginSize})，持仓比例设为0")
            ratio = 0.0
        else:
            try:
                ratio = marginSize / total_value
            except ZeroDivisionError:
                logger.error(f"{self.symbolName}计算持仓比例时发生除零错误，持仓比例设为0")
                ratio = 0.0
            except Exception as e:
                logger.error(f"{self.symbolName}计算持仓比例时发生错误: {e}，持仓比例设为0")
                ratio = 0.0
        
        if self.nowStockRadio != ratio:
            self.nowStockRadio = ratio
            logger.info(f"{self.symbolName}当前持仓比例更新为{ratio}({ratio*100}%)")

    #更新下单数量
    async def updateOrderAmount(self,orderAmount:float=None):
        if orderAmount is None:
            # 添加边界检查防止除零错误
            if self.lastPrice is None or self.lastPrice <= 0:
                logger.warning(f"{self.symbolName}价格信息无效({self.lastPrice})，使用最小订单数量")
                orderAmount = self.minOrderAmount
            elif self.equity is None or self.equity <= 0:
                logger.warning(f"{self.symbolName}账户权益无效({self.equity})，使用最小订单数量")
                orderAmount = self.minOrderAmount
            else:
                try:
                    orderAmount = self.equity/self.lastPrice*self.orderAmountRatio
                except ZeroDivisionError:
                    logger.error(f"{self.symbolName}计算订单数量时发生除零错误，使用最小订单数量")
                    orderAmount = self.minOrderAmount
                except Exception as e:
                    logger.error(f"{self.symbolName}计算订单数量时发生错误: {e}，使用最小订单数量")
                    orderAmount = self.minOrderAmount
        
        # 确保订单数量不小于最小值
        if orderAmount < self.minOrderAmount:
            logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            self.orderAmount = self.minOrderAmount
        else:
            self.orderAmount = orderAmount
            logger.info(f"{self.symbolName}当前下单数量更新为{self.orderAmount}")

    #更新未成交订单
    async def updateOrders(self,orders):
        async with self._update_lock:  # 使用锁保护
            oldOrderInfo = []
            for order in self.openOrders:
                oldOrderInfo.append({'id':order['id'],'side':order['side']})

            self.openOrders = orders
            if await tradeUtil.checkOpenOrder(self.openOrders):
                self.checkOrder = await tradeUtil.checkOpenOrder(self.openOrders)


    #计算下单数量
    async def calculateOrderAmount(self):
        #计算当前持仓占比占最大持仓占比的比例
        ratio = self.nowStockRadio/self.maxStockRadio
        #计算买单数量，买单数量与ratio成反比

    #计算买卖单价格
    async def calculateOrderPrice(self):
        #根据库存数量重构价差
        ratio = self.nowStockRadio/self.maxStockRadio
        buySpread,sellSpread = self.baseSpread,self.baseSpread
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

    #下单
    async def placeOrder(self,amount,price,side,reduceOnly):
        amount = round(amount,self.amountPrecision)
        price = round(price,self.pricePrecision)
        if amount < self.minOrderAmount:
            logger.warning(f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            amount = self.minOrderAmount
        try:
            order = await self.wsExchange.createOrder(self.symbolName, "limit",side,amount, price,{"reduceOnly":reduceOnly,"hedged": True})
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
        try:
            if await tradeUtil.checkOpenOrder(self.openOrders):
                logger.info(f"{self.symbolName}当前未成交订单数量为2，且1个买单和1个卖单，跳过挂单")
                return
            
            if len(self.openOrders) != 0:
                logger.info(f"{self.symbolName}当前未成交订单数量不是2，或不是1个买单和1个卖单，继续挂单")
                try:
                    await self.cancelAllOrder()
                except Exception as e:
                    logger.error(f"{self.symbolName}取消全部订单失败: {e}")

            try:
                buyPrice,sellPrice = await self.calculateOrderPrice()
                orderBuy = self.placeOrder(self.orderAmount,buyPrice,"buy",False)
                orderSell = None
                if self.nowStockRadio != 0:
                    orderSell = self.placeOrder(self.orderAmount,sellPrice,"sell",True)
                    b,s = await asyncio.gather(orderBuy,orderSell)
                    # 检查是否有订单下单失败
                    if not b or not s:
                        logger.warning(f"{self.symbolName}部分订单下单失败，买单: {b is not None}, 卖单: {s is not None}")
                        # 如果有订单失败，触发网络重连恢复
                        await self.networkHelper()
                        return
                    if self.websocketManager and b and s:
                        await self.websocketManager.runOpenOrderWatch(b,s)
                else:
                    b = await orderBuy
                    if not b:
                        logger.warning(f"{self.symbolName}买单下单失败")
                        # 如果买单失败，触发网络重连恢复
                        await self.networkHelper()
                        return
                    if self.websocketManager and b:
                        await self.websocketManager.runOpenOrderWatch(b)

            except Exception as e:
                logger.error(f"{self.symbolName}下单失败: {e}")
                # 下单异常时触发网络重连恢复
                await self.networkHelper()
                
        except Exception as e:
            logger.error(f"{self.symbolName}运行交易流程时发生错误: {e}")
            # 运行交易流程异常时触发网络重连恢复
            await self.networkHelper()

    #恢复模式下的交易流程（不触发networkHelper）
    async def runTradeInRecovery(self):
        """在恢复模式下执行交易逻辑，失败时不会再次触发networkHelper"""
        try:
            if await tradeUtil.checkOpenOrder(self.openOrders):
                logger.info(f"{self.symbolName}当前未成交订单数量为2，且1个买单和1个卖单，跳过挂单")
                return
            
            if len(self.openOrders) != 0:
                logger.info(f"{self.symbolName}当前未成交订单数量不是2，或不是1个买单和1个卖单，继续挂单")
                try:
                    await self.cancelAllOrder()
                except Exception as e:
                    logger.error(f"{self.symbolName}取消全部订单失败: {e}")
                    raise e

            try:
                buyPrice,sellPrice = await self.calculateOrderPrice()
                orderBuy = self.placeOrder(self.orderAmount,buyPrice,"buy",False)
                orderSell = None
                if self.nowStockRadio != 0:
                    orderSell = self.placeOrder(self.orderAmount,sellPrice,"sell",True)
                    b,s = await asyncio.gather(orderBuy,orderSell)
                    # 检查是否有订单下单失败
                    if not b or not s:
                        logger.error(f"{self.symbolName}恢复模式下部分订单下单失败，买单: {b is not None}, 卖单: {s is not None}")
                        raise Exception("恢复模式下订单下单失败")
                    if self.websocketManager and b and s:
                        await self.websocketManager.runOpenOrderWatch(b,s)
                else:
                    b = await orderBuy
                    if not b:
                        logger.error(f"{self.symbolName}恢复模式下买单下单失败")
                        raise Exception("恢复模式下买单下单失败")
                    if self.websocketManager and b:
                        await self.websocketManager.runOpenOrderWatch(b)

            except Exception as e:
                logger.error(f"{self.symbolName}恢复模式下单失败: {e}")
                raise e
                
        except Exception as e:
            logger.error(f"{self.symbolName}恢复模式运行交易流程时发生错误: {e}")
            raise e

    #网络重连函数
    async def networkHelper(self):
        if not self.networkError:
            self.networkError = True
            logger.info(f"{self.symbolName}开始网络错误恢复流程")
            while self.networkError:
                try:
                    # 等待一段时间后重新尝试交易
                    await asyncio.sleep(5)
                    # 重新获取最新状态
                    await self.refreshAllStatus()
                    # 重新执行交易逻辑（在恢复模式下执行）
                    await self.runTradeInRecovery()
                except Exception as e:
                    logger.error(f"{self.symbolName}恢复过程中发生错误，5s后重试: {e}")
                    await asyncio.sleep(5)
                else:
                    logger.info(f"{self.symbolName}网络错误恢复成功")
                    self.networkError = False
        else:
            logger.info(f"{self.symbolName}已经在处理网络错误中")

    #刷新所有状态信息
    async def refreshAllStatus(self):
        """刷新余额、订单、持仓等所有状态信息"""
        try:
            # 重新获取余额信息
            balance = await self.wsExchange.fetchBalance()
            await self.updateBalance(balance[self.coin]['free'], balance[self.coin]['total'])
            
            # 重新获取订单信息
            allOrder = await self.wsExchange.fetchOpenOrders(self.symbolName)
            targetOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)
            await self.updateOrders(targetOrder)
            
            # 重新获取持仓信息
            allPosition = await self.wsExchange.fetchPositions()
            await self.updatePosition(allPosition)
            
            # 重新获取价格信息
            ticker = await self.wsExchange.fetchTicker(self.symbolName)
            await self.updateLastPrice(float(ticker['last']))
            
            logger.info(f"{self.symbolName}状态信息刷新完成")
            
        except Exception as e:
            logger.error(f"{self.symbolName}刷新状态信息失败: {e}")
            raise e