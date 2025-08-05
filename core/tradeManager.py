from decimal import Decimal
import sys
from turtle import up
from util.sLogger import logger
from util import tradeUtil
import asyncio
from core.dataRecorder import data_recorder
import ccxt.pro
from config.config import get_trade_config


class TradeManager:
    def __init__(self,  symbolName: str, wsExchange: ccxt.pro.Exchange, baseSpread=0.001, minSpread=0.0008, maxSpread=0.003, orderCoolDown=0.1, maxStockRadio=0.25, orderAmountRatio=0.05, coin='USDT', direction='both'):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        # 价差需要除以2，因为是双边应用
        self.baseSpread = baseSpread/2
        self.minSpread = minSpread/2
        self.maxSpread = maxSpread/2
        self.balance: float = None
        self.equity: float = None
        self.lastPrice: float = None
        self.position = []
        self.orderAmount: float = None
        self.orderAmountRatio = orderAmountRatio
        # 下单冷却时间
        self.orderCoolDown = orderCoolDown
        self.openOrders = []
        # 最大持仓比例
        self.maxStockRadio = maxStockRadio
        self.nowStockRadio = 0.0
        self.lastBuyPrice = 0.0
        self.lastSellPrice = 0.0
        self.lastBuyOrderId = None
        self.lastSellOrderId = None
        self.checkOrder = False
        self._update_lock = asyncio.Lock()  # 添加锁
        self.networkError = False
        self.websocketManager = None
        self.coin = coin
        # 交易方向：'long'(只做多), 'short'(只做空), 'both'(双向)
        self.direction = direction
        # 双向持仓相关属性
        self.longPosition = None
        self.shortPosition = None
        self.netPosition = 0.0  # 净持仓数量
        self.longSize = 0.0     # 做多数量
        self.shortSize = 0.0    # 做空数量
        # 从配置文件读取配置项
        trade_config = get_trade_config()

        # 基于成交价的基准价功能
        self.useTransactionPrice = trade_config.USE_TRANSACTION_PRICE  # 是否使用成交价作为基准价的开关
        self.lastTransactionOrderPrice: float = None  # 最近一次成交订单的价格

        # 新增：订单状态监控和恢复机制
        self.lastTradeTime = None  # 最后一次交易时间
        self.lastOrderCheckTime = None  # 最后一次订单检查时间
        self.noOrderTimeout = trade_config.NO_ORDER_TIMEOUT  # 无订单超时时间（秒）
        self.orderCheckInterval = trade_config.ORDER_CHECK_INTERVAL  # 订单检查间隔（秒）

    # 创建完对象后必须调用这个函数
    async def initSymbolInfo(self):
        e = self.wsExchange
        # 初始化余额
        try:
            balance = await e.fetchBalance()
            logger.info(f"{self.symbolName}当前余额: {balance}")

            # 处理SUSDT余额问题，如果无法获取正确数量则使用假定值
            if self.coin == 'SUSDT':
                # 检查是否能正确获取SUSDT余额
                if self.coin in balance and balance[self.coin]['free'] > 0:
                    await self.updateBalance(balance[self.coin]['free'], balance[self.coin]['total'])
                else:
                    # 使用假定的SUSDT数量
                    assumed_susdt = 2534.7881
                    logger.warning(
                        f"无法正确获取{self.coin}余额，使用假定值: {assumed_susdt}")
                    await self.updateBalance(assumed_susdt, assumed_susdt)
            else:
                await self.updateBalance(balance[self.coin]['free'], balance[self.coin]['total'])
        except Exception as e:
            logger.error(f"初始化获取余额信息失败，终止程序: {e}")
            sys.exit(1)

        # 初始化交易对信息
        try:
            symbolInfo = await e.loadMarkets(self.symbolName)
            self.minOrderAmount = symbolInfo[self.symbolName]['limits']['amount']['min']
            pricePrecision = symbolInfo[self.symbolName]['precision']['price']
            amountPrecision = symbolInfo[self.symbolName]['precision']['amount']
            # 计算价格、下单数量的小数位数
            self.pricePrecision = abs(
                Decimal(str(pricePrecision)).as_tuple().exponent)
            self.amountPrecision = abs(
                Decimal(str(amountPrecision)).as_tuple().exponent)
            logger.info(
                f"{self.symbolName}：最小订单数量{self.minOrderAmount},价格精度小数位数{self.pricePrecision},数量精度小数位数{self.amountPrecision}")
            if self.orderAmount is not None:
                if self.orderAmount < self.minOrderAmount:
                    self.orderAmount = self.minOrderAmount
                    logger.warning(
                        f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            else:
                self.orderAmount = self.minOrderAmount
                logger.warning(
                    f"{self.symbolName}订单数量未设置，默认设置为最小订单数量{self.minOrderAmount}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化市场信息失败，终止程序: {e}")
            sys.exit(1)

        # 获取交易对价格
        try:
            ticker = await e.fetchTicker(self.symbolName)
            self.lastPrice = float(ticker['last'])
            logger.info(f"{self.symbolName}当前价格: {self.lastPrice}")
        except Exception as e:
            logger.error(f"{self.symbolName}获取交易对价格失败，终止程序: {e}")
            sys.exit(1)

        # 初始化未成交的订单信息
        try:
            allOrder = await e.fetchOpenOrders()
            openOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)
            self.openOrders = openOrder
            # logger.info(f"{self.symbolName}当前订单: {self.openOrders}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取订单信息失败，终止程序: {e}")
            sys.exit(1)

        # 初始化持仓信息
        try:
            allPosition = await e.fetchPositions()
            await self.updatePosition(allPosition)
            # logger.info(f"{self.symbolName}当前持仓: {self.position}")
        except Exception as e:
            logger.error(f"{self.symbolName}初始化获取持仓信息失败，终止程序: {e}")
            sys.exit(1)

        await self.updateOrderAmount()

        logger.info(f"{self.symbolName}初始化完成")

    async def bindWebsocketManager(self, websocketManager):
        self.websocketManager = websocketManager

    async def onOrderFilled(self, filled_orders=None):
        """
        处理订单成交后的逻辑
        """
        if filled_orders is None:
            filled_orders = []

        logger.info(f"{self.symbolName}处理订单成交事件，成交订单数量: {len(filled_orders)}")

        # 更新最后交易时间
        import time
        self.lastTradeTime = time.time()

        # 记录成交订单数据
        try:
            for order in filled_orders:
                if order and 'filled' in order and order['filled'] > 0:
                    # 更新最近成交订单价格
                    transaction_price = order['average'] or order['price']
                    if transaction_price:
                        self.lastTransactionOrderPrice = float(
                            transaction_price)
                        logger.info(
                            f"{self.symbolName}更新最近成交价格: {self.lastTransactionOrderPrice}")

                    # 计算手续费（如果订单中没有手续费信息，使用估算值）
                    fee = order.get('fee', {}).get('cost', 0)
                    if fee == 0 and 'cost' in order and order['cost'] is not None:
                        # 估算手续费为成交金额的0.1%
                        fee = order['cost'] * 0.0002

                    await data_recorder.record_trade(
                        symbol=self.symbolName,
                        side=order['side'],
                        amount=order['filled'],
                        price=transaction_price,
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
            await self.updateBalance(balance[self.coin]['free'], balance[self.coin]['total'])

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

    async def checkAndRecoverTrading(self):
        """
        检查交易状态并在需要时自动恢复挂单
        这个方法用于检测长时间无订单的情况并自动恢复
        """
        try:
            import time
            current_time = time.time()

            # 更新检查时间
            if self.lastOrderCheckTime is None:
                self.lastOrderCheckTime = current_time
                return

            # 检查是否到了检查间隔
            if (current_time - self.lastOrderCheckTime) < self.orderCheckInterval:
                return

            self.lastOrderCheckTime = current_time

            # 获取当前未成交订单
            allOrder = await self.wsExchange.fetchOpenOrders(self.symbolName)
            targetOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)

            # 检查是否长时间无订单
            has_no_orders = len(targetOrder) == 0
            is_timeout = False

            if has_no_orders:
                if self.lastTradeTime is None:
                    # 如果从未记录过交易时间，使用当前时间
                    self.lastTradeTime = current_time
                elif (current_time - self.lastTradeTime) >= self.noOrderTimeout:
                    is_timeout = True
            else:
                # 有订单时更新最后交易时间
                self.lastTradeTime = current_time

            # 如果长时间无订单，尝试恢复
            if has_no_orders and is_timeout:
                logger.warning(
                    f"{self.symbolName}检测到长时间无订单({self.noOrderTimeout}秒)，尝试自动恢复挂单")

                # 检查websocket监听状态
                if self.websocketManager and await self.websocketManager.isOrderWatchActive():
                    logger.info(f"{self.symbolName}停止无效的订单监听")
                    self.websocketManager.inWatchOpenOrder = False
                    self.websocketManager.openOrders = []

                # 重新执行交易逻辑
                await self.runTrade()
                logger.info(f"{self.symbolName}自动恢复挂单完成")

                # 重置最后交易时间
                self.lastTradeTime = current_time

            # 检查订单监听状态
            elif len(targetOrder) > 0:
                # 有订单但没有监听，尝试恢复监听
                if self.websocketManager and not await self.websocketManager.isOrderWatchActive():
                    logger.warning(f"{self.symbolName}发现有订单但无监听，恢复订单监听")
                    if len(targetOrder) == 2:
                        await self.websocketManager.runOpenOrderWatch(targetOrder[0], targetOrder[1])
                    else:
                        await self.websocketManager.runOpenOrderWatch(targetOrder[0])
                    logger.info(f"{self.symbolName}订单监听恢复成功")

        except Exception as e:
            logger.error(f"{self.symbolName}检查和恢复交易状态时发生错误: {e}")
            # 不触发networkHelper，避免过度重连

    # 更新余额
    async def updateBalance(self, balance: float, equity: float):
        self.balance = balance
        self.equity = equity
        logger.info(
            f"{self.symbolName}当前余额: {self.balance},当前权益: {self.equity}")

        # 更新数据记录器中的权益信息
        try:
            await data_recorder.update_equity(equity)
        except Exception as e:
            logger.error(f"{self.symbolName}更新权益数据时发生错误: {e}")

    # 更新最新价格
    async def updateLastPrice(self, lastPrice: float):
        if self.lastPrice != lastPrice:
            self.lastPrice = lastPrice
            
            # 记录价格数据到数据记录器
            try:
                await data_recorder.record_price(self.symbolName, lastPrice)
            except Exception as e:
                logger.error(f"{self.symbolName}记录价格数据时发生错误: {e}")

        # 初始化价格触发冷却时间
        if not hasattr(self, '_last_price_trigger_time'):
            self._last_price_trigger_time = 0

        # 只在单边交易模式（只做多或只做空）且无持仓时才进行追单
        # 双向模式下不需要追单，因为价格两边都能挂单
        if (self.direction in ['long', 'short'] and
                await tradeUtil.positionMarginSize(self.position, self.symbolName) == 0):

            # 检查是否有相应的价格记录
            has_price_record = False
            if self.direction == 'long' and self.lastBuyPrice != 0.0:
                has_price_record = True
            elif self.direction == 'short' and hasattr(self, 'lastSellPrice') and self.lastSellPrice != 0.0:
                has_price_record = True

            if not has_price_record:
                return

            import time
            current_time = time.time()

            # 增加冷却机制，避免频繁触发（至少间隔5秒）
            if current_time - self._last_price_trigger_time < 5:
                return

            # 只做多模式：当价格超过最新买单价一定范围时重新挂买单
            # 只做空模式：当价格低于最新卖单价一定范围时重新挂卖单
            should_retrade = False
            if self.direction == 'long' and lastPrice > self.lastBuyPrice * (1 + self.baseSpread):
                logger.info(
                    f"{self.symbolName}只做多模式，无持仓且最新价格{lastPrice}超过最新买单价{self.lastBuyPrice}*(1+{self.baseSpread})，重新挂买单")
                should_retrade = True
            elif (self.direction == 'short' and hasattr(self, 'lastSellPrice') and
                  self.lastSellPrice != 0.0 and lastPrice < self.lastSellPrice * (1 - self.baseSpread)):
                logger.info(
                    f"{self.symbolName}只做空模式，无持仓且最新价格{lastPrice}低于最新卖单价{self.lastSellPrice}*(1-{self.baseSpread})，重新挂卖单")
                should_retrade = True

            if should_retrade:
                # 计算期望订单，检查是否真的需要重新下单
                expected_orders = self._calculate_expected_orders()
                if not self._check_orders_match_expected(expected_orders):
                    logger.info(f"{self.symbolName}订单状态不符合预期，执行重新挂单")
                    self._last_price_trigger_time = current_time
                    await self.runTrade()
                else:
                    logger.debug(f"{self.symbolName}虽然价格触发条件满足，但订单状态符合预期，跳过挂单")

        # 定期检查订单监听状态（每100次价格更新检查一次）
        if not hasattr(self, '_price_update_counter'):
            self._price_update_counter = 0
        self._price_update_counter += 1

        if self._price_update_counter % 100 == 0:
            await self.checkAndRecoverOrderWatch()

    def setUseTransactionPrice(self, enabled: bool):
        """
        设置是否使用成交价作为基准价

        Args:
            enabled (bool): True表示启用成交价基准，False表示使用实时价格基准
        """
        self.useTransactionPrice = enabled
        status = "启用" if enabled else "禁用"
        logger.info(f"{self.symbolName}{status}成交价基准功能")

        if enabled and self.lastTransactionOrderPrice is not None:
            logger.info(
                f"{self.symbolName}当前成交价基准: {self.lastTransactionOrderPrice}")
        elif enabled:
            logger.warning(f"{self.symbolName}启用成交价基准但暂无成交记录，将在首次成交后生效")

    def getTransactionPriceStatus(self):
        """
        获取成交价基准功能的状态信息

        Returns:
            dict: 包含功能状态和当前成交价的字典
        """
        return {
            'enabled': self.useTransactionPrice,
            'lastTransactionPrice': self.lastTransactionOrderPrice,
            'currentPrice': self.lastPrice
        }

    # 更新持仓
    async def updatePosition(self, position):
        self.position = position

        # 获取双向持仓信息
        self.longPosition = await tradeUtil.getPositionBySide(position, self.symbolName, 'long')
        self.shortPosition = await tradeUtil.getPositionBySide(position, self.symbolName, 'short')

        # 计算净持仓数量
        self.netPosition, self.longSize, self.shortSize = await tradeUtil.calculateNetPosition(position, self.symbolName)

        # 计算总保证金
        marginSize = await tradeUtil.positionMarginSize(self.position, self.symbolName)

        # 添加边界检查防止除零错误和None值错误
        if self.balance is None:
            logger.warning(f"{self.symbolName}余额为None，持仓比例设为0")
            ratio = 0.0
            self.nowStockRadio = ratio
            return
        
        total_value = self.balance + marginSize
        if total_value <= 0:
            logger.warning(
                f"{self.symbolName}总资产为0或负数(余额:{self.balance}, 保证金:{marginSize})，持仓比例设为0")
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
            logger.info(
                f"{self.symbolName}持仓详情 - 做多:{self.longSize}, 做空:{self.shortSize}, 净持仓:{self.netPosition}")

    # 更新下单数量
    async def updateOrderAmount(self, orderAmount: float = None):
        logger.debug(
            f"{self.symbolName}更新订单数量: 传入参数={orderAmount}, 当前权益={self.equity}, 当前价格={self.lastPrice}")

        if orderAmount is None:
            # 添加边界检查防止除零错误
            if self.lastPrice is None or self.lastPrice <= 0:
                logger.warning(
                    f"{self.symbolName}价格信息无效({self.lastPrice})，使用最小订单数量")
                orderAmount = self.minOrderAmount
            elif self.equity is None or self.equity <= 0:
                logger.warning(
                    f"{self.symbolName}账户权益无效({self.equity})，使用最小订单数量")
                orderAmount = self.minOrderAmount
            else:
                try:
                    orderAmount = self.equity/self.lastPrice*self.orderAmountRatio
                    logger.debug(
                        f"{self.symbolName}计算订单数量: {self.equity}/{self.lastPrice}*{self.orderAmountRatio}={orderAmount}")
                except ZeroDivisionError:
                    logger.error(f"{self.symbolName}计算订单数量时发生除零错误，使用最小订单数量")
                    orderAmount = self.minOrderAmount
                except Exception as e:
                    logger.error(f"{self.symbolName}计算订单数量时发生错误: {e}，使用最小订单数量")
                    orderAmount = self.minOrderAmount

        # 确保订单数量不小于最小值
        if orderAmount < self.minOrderAmount:
            logger.warning(
                f"{self.symbolName}订单数量({orderAmount})小于最小订单数量({self.minOrderAmount})，已设置为最小订单数量")
            self.orderAmount = self.minOrderAmount
        else:
            self.orderAmount = orderAmount

        # 从配置文件读取最小订单价值
        trade_config = get_trade_config()
        minOrderValue = getattr(
            trade_config, 'MIN_ORDER_VALUE', 5.5)  # 默认5.5 USDT

        # 校验订单价值
        if self.lastPrice and self.lastPrice > 0:
            current_value = self.orderAmount * self.lastPrice
            if current_value < minOrderValue:
                self.orderAmount = minOrderValue / self.lastPrice
                logger.info(
                    f"{self.symbolName}订单价值({current_value:.2f})小于最小价值({minOrderValue})，调整订单数量为{self.orderAmount:.6f}")

        logger.info(f"{self.symbolName}订单数量更新完成: {self.orderAmount:.6f}")

    # 更新未成交订单
    async def updateOrders(self, orders):
        async with self._update_lock:  # 使用锁保护
            oldOrderInfo = []
            for order in self.openOrders:
                oldOrderInfo.append({'id': order['id'], 'side': order['side']})

            self.openOrders = orders
            if await tradeUtil.checkOpenOrder(self.openOrders):
                self.checkOrder = await tradeUtil.checkOpenOrder(self.openOrders)

    # 计算下单数量

    async def calculateOrderAmount(self):
        """动态计算订单数量，根据持仓比例调整"""
        try:
            # 计算当前持仓占比占最大持仓占比的比例
            ratio = self.nowStockRadio / self.maxStockRadio if self.maxStockRadio > 0 else 0

            # 基础订单数量（根据账户权益和配置比例计算）
            if self.equity and self.lastPrice and self.equity > 0 and self.lastPrice > 0:
                base_amount = self.equity / self.lastPrice * self.orderAmountRatio
            else:
                base_amount = self.minOrderAmount
                logger.warning(f"{self.symbolName}无法计算基础订单数量，使用最小订单数量")

            # 根据持仓比例调整订单数量
            # 持仓比例越高，订单数量越小（降低风险）
            if ratio > 0.8:  # 高持仓比例
                adjusted_amount = base_amount * 0.5
            elif ratio > 0.5:  # 中等持仓比例
                adjusted_amount = base_amount * 0.75
            else:  # 低持仓比例或无持仓
                adjusted_amount = base_amount

            # 确保不小于最小订单数量
            final_amount = max(adjusted_amount, self.minOrderAmount)

            # 更新订单数量
            await self.updateOrderAmount(final_amount)

            logger.info(
                f"{self.symbolName}动态计算订单数量: 基础={base_amount:.6f}, 持仓比例={ratio:.3f}, 最终={final_amount:.6f}")

        except Exception as e:
            logger.error(f"{self.symbolName}计算订单数量时发生错误: {e}，使用最小订单数量")
            await self.updateOrderAmount(self.minOrderAmount)

    # 计算买卖单价格
    async def calculateOrderPrice(self):
        # 根据交易方向和库存数量重构价差
        if self.direction == 'both':
            # 双向持仓：使用总持仓比例
            ratio = self.nowStockRadio/self.maxStockRadio
        elif self.direction == 'long':
            # 只做多：只考虑多头持仓比例
            long_margin = abs(
                self.longSize * self.lastPrice) if self.longSize else 0
            total_value = self.balance + long_margin
            ratio = (long_margin / total_value /
                     self.maxStockRadio) if total_value > 0 else 0
        elif self.direction == 'short':
            # 只做空：只考虑空头持仓比例
            short_margin = abs(
                self.shortSize * self.lastPrice) if self.shortSize else 0
            total_value = self.balance + short_margin
            ratio = (short_margin / total_value /
                     self.maxStockRadio) if total_value > 0 else 0
        else:
            ratio = 0

        buySpread, sellSpread = self.baseSpread, self.baseSpread
        balanceRatio = 0.5

        '''
        价差计算逻辑：
        - 当 ratio = 0 时, spread = minSpread
        - 当 0 < ratio <= 0.5 时, spread 从 minSpread 线性增长到 baseSpread
        - 当 0.5 < ratio <= 1 时, spread 从 baseSpread 线性增长到 maxSpread
        
        对于单向交易：
        - long模式：持仓越多，买单价差越大（降低买入积极性），卖单价差越小（提高卖出积极性）
        - short模式：持仓越多，卖单价差越大（降低卖出积极性），买单价差越小（提高买入积极性）
        '''

        if self.direction == 'long':
            # 只做多：持仓越多，买单价差越大，卖单价差越小
            if ratio < balanceRatio:
                buySpread = 2 * (self.baseSpread-self.minSpread) * \
                    ratio + self.minSpread
                sellSpread = 2 * (self.baseSpread -
                                  self.maxSpread) * ratio + self.maxSpread
            else:
                buySpread = 2 * (self.maxSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread
                sellSpread = 2 * (self.minSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread
        elif self.direction == 'short':
            # 只做空：持仓越多，卖单价差越大，买单价差越小
            if ratio < balanceRatio:
                sellSpread = 2 * (self.baseSpread -
                                  self.minSpread) * ratio + self.minSpread
                buySpread = 2 * (self.baseSpread-self.maxSpread) * \
                    ratio + self.maxSpread
            else:
                sellSpread = 2 * (self.maxSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread
                buySpread = 2 * (self.minSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread
        else:
            # 双向持仓：原有逻辑
            if ratio < balanceRatio:
                buySpread = 2 * (self.baseSpread-self.minSpread) * \
                    ratio + self.minSpread
                sellSpread = 2 * (self.baseSpread -
                                  self.maxSpread) * ratio + self.maxSpread
            else:
                buySpread = 2 * (self.maxSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread
                sellSpread = 2 * (self.minSpread-self.baseSpread) * \
                    (ratio - balanceRatio) + self.baseSpread

        # 确保价差在合理范围内
        buySpread = max(self.minSpread, min(self.maxSpread, buySpread))
        sellSpread = max(self.minSpread, min(self.maxSpread, sellSpread))

        print(
            f"交易方向:{self.direction}, 默认价差:{self.baseSpread}, 当前持仓比例:{ratio:.4f}, 买单价差:{buySpread:.6f}, 卖单价差:{sellSpread:.6f}")

        # 确定用于计算价格的基准价
        if self.useTransactionPrice and self.lastTransactionOrderPrice is not None:
            # 使用最近成交订单价格作为基准价
            basePrice = self.lastTransactionOrderPrice
            logger.info(f"{self.symbolName}使用成交价作为基准价: {basePrice}")
        else:
            # 使用实时价格作为基准价
            basePrice = self.lastPrice
            if self.useTransactionPrice and self.lastTransactionOrderPrice is None:
                logger.warning(
                    f"{self.symbolName}启用了成交价基准但无成交记录，使用实时价格: {basePrice}")

        # 计算买卖价格
        buyPrice = basePrice * (1 - buySpread)
        sellPrice = basePrice * (1 + sellSpread)
        return buyPrice, sellPrice

    # 下单
    async def placeOrder(self, amount, price, side, reduceOnly):
        amount = round(amount, self.amountPrecision)
        price = round(price, self.pricePrecision)
        if amount < self.minOrderAmount:
            logger.warning(
                f"订单数量不能小于最小订单数量{self.minOrderAmount}，已设置为该交易对的最小订单数量")
            amount = self.minOrderAmount
        try:
            order = await self.wsExchange.create_order(self.symbolName, "limit", side, amount, price, {"reduceOnly": reduceOnly, "hedged": True})
        except Exception as e:
            logger.error(f"{self.symbolName}下单失败: {e}")
            return None
        else:
            logger.info(
                f"{self.symbolName}下单成功: {order['id']},下单数量: {amount},下单价格: {price},方向: {side}")
            if side == "buy":
                self.lastBuyPrice = self.lastPrice
            elif side == "sell":
                self.lastSellPrice = self.lastPrice
            return order

    # 取消全部订单
    async def cancelAllOrder(self):
        try:
            await self.wsExchange.cancelAllOrders(self.symbolName)
        except Exception as e:
            logger.error(f"{self.symbolName}取消全部订单失败: {e}")
            return False
        else:
            logger.info(f"{self.symbolName}取消全部订单成功")
            return True

    # 运行流程
    async def runTrade(self):
        try:
            logger.info(f"{self.symbolName}开始执行交易流程")

            # 重新计算订单数量（根据当前持仓和市场状况）
            await self.calculateOrderAmount()

            # 检查必要的交易条件
            if self.orderAmount is None or self.orderAmount <= 0:
                logger.error(
                    f"{self.symbolName}订单数量无效: {self.orderAmount}，跳过交易")
                return

            if self.lastPrice is None or self.lastPrice <= 0:
                logger.error(f"{self.symbolName}价格信息无效: {self.lastPrice}，跳过交易")
                return

            # 计算期望的订单数量
            expected_orders = self._calculate_expected_orders()
            logger.info(
                f"{self.symbolName}期望订单数量: {len(expected_orders)}, 详情: {[o['type'] for o in expected_orders]}")

            # 检查当前订单是否符合期望
            if self._check_orders_match_expected(expected_orders):
                logger.info(f"{self.symbolName}当前订单状态符合预期，跳过挂单")
                return

            # 取消所有不符合预期的订单
            if len(self.openOrders) > 0:
                logger.info(f"{self.symbolName}当前订单状态不符合预期，取消所有订单")
                try:
                    await self.cancelAllOrder()
                    # 等待取消完成
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"{self.symbolName}取消全部订单失败: {e}")

            try:
                buyPrice, sellPrice = await self.calculateOrderPrice()
                logger.info(
                    f"{self.symbolName}计算订单价格: 买入={buyPrice}, 卖出={sellPrice}, 数量={self.orderAmount}")
                orders_to_place = []

                # 根据期望订单列表下单
                for order_info in expected_orders:
                    side = order_info['side']
                    reduce_only = order_info['reduce_only']
                    price = buyPrice if side == 'buy' else sellPrice
                    logger.info(
                        f"{self.symbolName}准备下单: {side} {self.orderAmount} @ {price} (reduce_only={reduce_only})")
                    orders_to_place.append(self.placeOrder(
                        self.orderAmount, price, side, reduce_only))

                # 执行下单
                if len(orders_to_place) == 0:
                    logger.warning(f"{self.symbolName}没有需要下单的订单")
                    return
                elif len(orders_to_place) == 1:
                    logger.info(f"{self.symbolName}执行单个订单下单")
                    order = await orders_to_place[0]
                    if not order:
                        logger.warning(f"{self.symbolName}订单下单失败")
                        await self.networkHelper()
                        return
                    logger.info(
                        f"{self.symbolName}订单下单成功: {order.get('id', 'unknown')}")
                    if self.websocketManager and order:
                        await self.websocketManager.runOpenOrderWatch(order)
                elif len(orders_to_place) > 1:
                    logger.info(
                        f"{self.symbolName}执行批量订单下单，数量: {len(orders_to_place)}")
                    results = await asyncio.gather(*orders_to_place, return_exceptions=True)
                    successful_orders = [
                        r for r in results if r is not None and not isinstance(r, Exception)]
                    failed_orders = [
                        r for r in results if isinstance(r, Exception)]

                    if failed_orders:
                        logger.error(
                            f"{self.symbolName}部分订单下单失败: {[str(e) for e in failed_orders]}")

                    if len(successful_orders) != len(orders_to_place):
                        logger.warning(
                            f"{self.symbolName}部分订单下单失败，成功: {len(successful_orders)}/{len(orders_to_place)}")
                        await self.networkHelper()
                        return

                    logger.info(
                        f"{self.symbolName}批量订单下单成功，数量: {len(successful_orders)}")
                    if self.websocketManager and successful_orders:
                        await self.websocketManager.runOpenOrderWatch(*successful_orders)

            except Exception as e:
                logger.error(f"{self.symbolName}下单失败: {e}")
                await self.networkHelper()

        except Exception as e:
            logger.error(f"{self.symbolName}运行交易流程时发生错误: {e}")
            await self.networkHelper()

    def _calculate_expected_orders(self):
        """计算期望的订单列表"""
        orders = []

        if self.direction == 'long':
            # 只做多模式
            if self.longSize == 0:
                # 无持仓时：只下开多订单
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
            else:
                # 有持仓时：下开多订单和平多订单
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
                orders.append(
                    {'side': 'sell', 'reduce_only': True, 'type': '平多'})

        elif self.direction == 'short':
            # 只做空模式
            if self.shortSize == 0:
                # 无持仓时：只下开空订单
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
            else:
                # 有持仓时：下开空订单和平空订单
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
                orders.append(
                    {'side': 'buy', 'reduce_only': True, 'type': '平空'})

        elif self.direction == 'both':
            # 双向模式
            if self.longSize == 0 and self.shortSize == 0:
                # 无持仓时：下开多和开空订单
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
            elif self.shortSize > 0 and self.longSize == 0:
                # 有空头持仓但没有多头持仓
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
                orders.append(
                    {'side': 'buy', 'reduce_only': True, 'type': '平空'})
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
            elif self.longSize > 0 and self.shortSize == 0:
                # 有多头持仓但没有空头持仓
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
                orders.append(
                    {'side': 'sell', 'reduce_only': True, 'type': '平多'})
            else:
                # 双向都有持仓
                orders.append(
                    {'side': 'buy', 'reduce_only': False, 'type': '开多'})
                orders.append(
                    {'side': 'buy', 'reduce_only': True, 'type': '平空'})
                orders.append(
                    {'side': 'sell', 'reduce_only': False, 'type': '开空'})
                orders.append(
                    {'side': 'sell', 'reduce_only': True, 'type': '平多'})

        return orders

    def _check_orders_match_expected(self, expected_orders):
        """检查当前订单是否符合期望"""
        if len(self.openOrders) != len(expected_orders):
            return False

        # 统计期望订单的类型
        expected_buy_open = sum(
            1 for o in expected_orders if o['side'] == 'buy' and not o['reduce_only'])
        expected_buy_close = sum(
            1 for o in expected_orders if o['side'] == 'buy' and o['reduce_only'])
        expected_sell_open = sum(
            1 for o in expected_orders if o['side'] == 'sell' and not o['reduce_only'])
        expected_sell_close = sum(
            1 for o in expected_orders if o['side'] == 'sell' and o['reduce_only'])

        # 统计当前订单的类型
        current_buy_orders = [
            o for o in self.openOrders if o.get('side') == 'buy']
        current_sell_orders = [
            o for o in self.openOrders if o.get('side') == 'sell']

        # 检查买卖单数量是否匹配
        expected_buy_total = expected_buy_open + expected_buy_close
        expected_sell_total = expected_sell_open + expected_sell_close

        if len(current_buy_orders) != expected_buy_total or len(current_sell_orders) != expected_sell_total:
            return False

        # 增加价格偏差检查：如果当前价格与订单价格偏差过大，需要重新下单
        if hasattr(self, 'lastPrice') and self.lastPrice:
            # 从配置文件读取价格偏差阈值系数
            trade_config = get_trade_config()
            deviation_factor = getattr(
                trade_config, 'PRICE_DEVIATION_FACTOR', 0.5)  # 默认0.5
            price_deviation_threshold = self.baseSpread * deviation_factor  # 价格偏差阈值

            # 检查买单价格偏差
            for buy_order in current_buy_orders:
                order_price = float(buy_order.get('price', 0))
                if order_price > 0:
                    # 买单应该低于当前价格，检查偏差是否过大
                    price_diff = abs(self.lastPrice -
                                     order_price) / self.lastPrice
                    if price_diff > price_deviation_threshold:
                        logger.info(
                            f"{self.symbolName}买单价格偏差过大: 当前价格{self.lastPrice}, 订单价格{order_price}, 偏差{price_diff:.4f}")
                        return False

            # 检查卖单价格偏差
            for sell_order in current_sell_orders:
                order_price = float(sell_order.get('price', 0))
                if order_price > 0:
                    # 卖单应该高于当前价格，检查偏差是否过大
                    price_diff = abs(
                        order_price - self.lastPrice) / self.lastPrice
                    if price_diff > price_deviation_threshold:
                        logger.info(
                            f"{self.symbolName}卖单价格偏差过大: 当前价格{self.lastPrice}, 订单价格{order_price}, 偏差{price_diff:.4f}")
                        return False

        return True

    # 恢复模式下的交易流程（不触发networkHelper）
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
                buyPrice, sellPrice = await self.calculateOrderPrice()
                orderBuy = self.placeOrder(
                    self.orderAmount, buyPrice, "buy", False)
                orderSell = None
                if self.nowStockRadio != 0:
                    orderSell = self.placeOrder(
                        self.orderAmount, sellPrice, "sell", True)
                    b, s = await asyncio.gather(orderBuy, orderSell)
                    # 检查是否有订单下单失败
                    if not b or not s:
                        logger.error(
                            f"{self.symbolName}恢复模式下部分订单下单失败，买单: {b is not None}, 卖单: {s is not None}")
                        raise Exception("恢复模式下订单下单失败")
                    if self.websocketManager and b and s:
                        await self.websocketManager.runOpenOrderWatch(b, s)
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

    # 网络重连函数
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

    # 刷新所有状态信息
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
