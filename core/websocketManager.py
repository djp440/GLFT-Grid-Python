from util import tradeUtil
from util.sLogger import logger
import ccxt
import ccxt.pro
import asyncio
from core.tradeManager import TradeManager


class WebSocketManager:
    def __init__(self, symbolName: str, wsExchange: ccxt.pro.Exchange, tradeManage: TradeManager, run=True):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        self.tradeManager = tradeManage
        self.run = run
        self.inWatchOpenOrder = False
        self.openOrders = []

    async def watchTicker(self):
        logger.info(f"{self.symbolName}价格获取websocket模块启动")
        while self.run:
            try:
                # ticker = await self.wsExchange.watchTicker(self.symbolName)
                #  # logger.info(f"{self.symbolName}当前价格: {ticker['last']}")
                # await self.tradeManager.updateLastPrice(float(ticker['last']))
                orderbook = await self.wsExchange.watchOrderBook(self.symbolName)
                # logger.info(f"{self.symbolName}当前订单簿: {orderbook}")
                bid = orderbook['bids'][0][0]
                ask = orderbook['asks'][0][0]
                await self.tradeManager.updateLastPrice(float(((bid+ask)/2)))
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}价格获取网络错误: {e}")
                await self.tradeManager.networkHelper()
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}价格获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}价格获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"{self.symbolName}价格获取未知错误: {e}")

    async def watchMyPosition(self):
        logger.info(f"{self.symbolName}持仓获取websocket模块启动")
        while self.run:
            try:
                position = await self.wsExchange.watchPositions()
                #   logger.info(f"{self.symbolName}当前持仓: {position}")
                await self.tradeManager.updatePosition(position)
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}持仓获取网络错误: {e}")
                await self.tradeManager.networkHelper()
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}持仓获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}持仓获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"{self.symbolName}持仓获取未知错误: {e}")

    async def watchMyBalance(self):
        logger.info(f"{self.symbolName}余额获取websocket模块启动")
        while self.run:
            try:
                balance = await self.wsExchange.watchBalance()
                await self.tradeManager.updateBalance(float(balance[self.tradeManager.coin]['free']), float(balance[self.tradeManager.coin]['total']))
            except ccxt.NetworkError as e:
                logger.error(f"余额获取网络错误: {e}")
                await self.tradeManager.networkHelper()
            except ccxt.ExchangeError as e:
                logger.error(f"余额获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"余额获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"余额获取未知错误: {e}")

    async def watchMyOrder(self):
        self.wsExchange.newUpdates = False
        logger.info(f"{self.symbolName}订单获取websocket模块启动")
        while self.run:
            try:
                allOrder = await self.wsExchange.watchOrders()
                # logger.info(f"当前全部订单: {allOrder}")
                targetOrder = await tradeUtil.openOrderFilter(allOrder, self.symbolName)
                # logger.info(f"{self.symbolName}当前订单: {targetOrder}")
                await self.tradeManager.updateOrders(targetOrder)
            except ccxt.NetworkError as e:
                logger.error(f"{self.symbolName}订单获取网络错误: {e}")
                await self.tradeManager.networkHelper()
            except ccxt.ExchangeError as e:
                logger.error(f"{self.symbolName}订单获取交易所错误: {e}")
            except asyncio.CancelledError:
                logger.info(f"{self.symbolName}订单获取任务已取消")
                self.run = False
            except Exception as e:
                logger.error(f"{self.symbolName}订单获取未知错误: {e}")

    async def runOpenOrderWatch(self, *orders):
        # 提取订单ID列表
        order_ids = []
        for order in orders:
            if order is not None:
                if isinstance(order, dict) and 'id' in order:
                    order_ids.append(order['id'])
                else:
                    order_ids.append(str(order))

        self.openOrders = order_ids
        self.inWatchOpenOrder = True
        logger.info(f"接收到{self.symbolName}订单监控需求: {order_ids}")

    async def isOrderWatchActive(self):
        """检查订单监听是否活跃"""
        return self.inWatchOpenOrder and len(self.openOrders) > 0

    async def watchOpenOrder(self):
        logger.info(f"{self.symbolName}未成交订单获取websocket模块启动")
        while self.run:
            if self.inWatchOpenOrder:
                try:
                    allOrder = await self.wsExchange.watchOrders()

                    # 只处理当前监听的订单，过滤掉不相关的订单更新
                    relevant_orders = []
                    for order in allOrder:
                        if str(order['id']) in [str(oid) for oid in self.openOrders]:
                            relevant_orders.append(order)

                    # 只在有相关订单更新时才记录日志
                    if relevant_orders:
                        logger.info(f"监听到相关订单更新: {len(relevant_orders)}个订单")
                        logger.info(f"当前监听的订单ID: {self.openOrders}")
                        logger.info(
                            f"收到的相关订单ID: {[str(o['id']) for o in relevant_orders]}")

                    # 检查监听的订单是否有成交
                    filled_orders = []
                    for order_id in self.openOrders:
                        order_found = False
                        for order in relevant_orders:
                            # 确保订单ID比较时类型一致
                            if str(order['id']) == str(order_id):
                                order_found = True
                                # 检查订单状态是否为已成交或部分成交
                                if order['status'] in ['closed', 'filled']:
                                    filled_orders.append(order)
                                    logger.info(
                                        f"{self.symbolName}订单{order_id}已成交: {order['side']} {order['amount']} @ {order['price']}")
                                break

                        # 如果订单在相关订单中找不到，说明可能已经完全成交并从未成交列表中移除
                        if not order_found:
                            logger.info(
                                f"{self.symbolName}订单{order_id}已从未成交列表中消失，可能已完全成交")

                    # 如果有订单成交，通知tradeManager进行后续处理
                    if filled_orders or len([oid for oid in self.openOrders if not any(str(o['id']) == str(oid) for o in relevant_orders)]) > 0:
                        logger.info(
                            f"{self.symbolName}检测到订单成交，通知TradeManager进行后续处理")
                        # 先停止当前监听，避免重复处理
                        self.inWatchOpenOrder = False
                        self.openOrders = []
                        # 然后通知tradeManager进行后续处理
                        try:
                            await self.tradeManager.onOrderFilled(filled_orders)
                        except Exception as e:
                            logger.error(
                                f"{self.symbolName}通知TradeManager处理订单成交时发生错误: {e}")
                            # 如果处理失败，重新启动监听以防止程序卡死
                            await asyncio.sleep(1)
                            continue

                except ccxt.NetworkError as e:
                    logger.error(f"{self.symbolName}订单获取网络错误: {e}")
                    await self.tradeManager.networkHelper()
                except ccxt.ExchangeError as e:
                    logger.error(f"{self.symbolName}订单获取交易所错误: {e}")
                except asyncio.CancelledError:
                    logger.info(f"{self.symbolName}订单获取任务已取消")
                    self.run = False
                except Exception as e:
                    logger.error(f"{self.symbolName}订单获取未知错误: {e}")
            else:
                await asyncio.sleep(0.1)
