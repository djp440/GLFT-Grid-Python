from util import tradeUtil
from util.sLogger import logger
import ccxt
import ccxt.pro
import asyncio
from core.tradeManager import TradeManager
from config.config import get_websocket_config


class WebSocketManager:
    def __init__(self, symbolName: str, wsExchange: ccxt.pro.Exchange, tradeManage: TradeManager, run=True):
        self.symbolName = symbolName
        self.wsExchange = wsExchange
        self.tradeManager = tradeManage
        self.run = run
        self.inWatchOpenOrder = False
        self.openOrders = []
        # 新增：订单监听增强机制
        self.orderWatchStartTime = None  # 订单监听开始时间
        self.lastOrderCheckTime = None   # 最后一次主动检查时间
        
        # 从配置文件读取配置项
        ws_config = get_websocket_config()
        self.orderCheckInterval = ws_config.ORDER_CHECK_INTERVAL    # 主动检查间隔（秒）
        self.orderWatchTimeout = ws_config.ORDER_WATCH_TIMEOUT      # 订单监听超时时间（秒）

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
        # 新增：记录监听开始时间
        import time
        self.orderWatchStartTime = time.time()
        self.lastOrderCheckTime = time.time()
        logger.info(f"接收到{self.symbolName}订单监控需求: {order_ids}，开始时间: {self.orderWatchStartTime}")

    async def isOrderWatchActive(self):
        """检查订单监听是否活跃"""
        return self.inWatchOpenOrder and len(self.openOrders) > 0
    
    async def _activeCheckOrderStatus(self):
        """主动检查订单状态（用于检测瞬间成交的订单）"""
        if not self.inWatchOpenOrder or len(self.openOrders) == 0:
            return []
        
        try:
            # 获取当前所有未成交订单
            allOpenOrders = await self.wsExchange.fetchOpenOrders(self.symbolName)
            
            # 检查我们监听的订单是否还在未成交列表中
            missing_orders = []
            for order_id in self.openOrders:
                order_found = False
                for open_order in allOpenOrders:
                    if str(open_order['id']) == str(order_id):
                        order_found = True
                        break
                
                if not order_found:
                    # 订单不在未成交列表中，可能已经成交
                    missing_orders.append(order_id)
                    logger.info(f"{self.symbolName}主动检查发现订单{order_id}已不在未成交列表中")
            
            # 如果有订单消失，尝试获取这些订单的详细信息
            filled_orders = []
            for order_id in missing_orders:
                try:
                    # 尝试获取订单详情
                    order_detail = await self.wsExchange.fetchOrder(order_id, self.symbolName)
                    if order_detail and order_detail.get('status') in ['closed', 'filled']:
                        filled_orders.append(order_detail)
                        logger.info(f"{self.symbolName}主动检查确认订单{order_id}已成交: {order_detail.get('side')} {order_detail.get('filled')} @ {order_detail.get('average') or order_detail.get('price')}")
                except Exception as e:
                    logger.warning(f"{self.symbolName}获取订单{order_id}详情失败: {e}")
                    # 即使获取详情失败，也认为订单可能已成交
                    filled_orders.append({'id': order_id, 'status': 'filled', 'filled': 0})
            
            return filled_orders
            
        except Exception as e:
            logger.error(f"{self.symbolName}主动检查订单状态时发生错误: {e}")
            return []

    async def watchOpenOrder(self):
        logger.info(f"{self.symbolName}未成交订单获取websocket模块启动")
        while self.run:
            if self.inWatchOpenOrder:
                try:
                    import time
                    current_time = time.time()
                    
                    # 检查是否需要进行主动检查
                    should_active_check = False
                    if self.lastOrderCheckTime is None or (current_time - self.lastOrderCheckTime) >= self.orderCheckInterval:
                        should_active_check = True
                        self.lastOrderCheckTime = current_time
                    
                    # 检查是否超时
                    if self.orderWatchStartTime and (current_time - self.orderWatchStartTime) >= self.orderWatchTimeout:
                        logger.warning(f"{self.symbolName}订单监听超时({self.orderWatchTimeout}秒)，执行主动检查")
                        should_active_check = True
                    
                    # 执行主动检查
                    active_check_filled_orders = []
                    if should_active_check:
                        logger.info(f"{self.symbolName}执行主动订单状态检查")
                        active_check_filled_orders = await self._activeCheckOrderStatus()
                        if active_check_filled_orders:
                            logger.info(f"{self.symbolName}主动检查发现{len(active_check_filled_orders)}个已成交订单")
                    
                    # 正常的websocket监听
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
                    websocket_filled_orders = []
                    missing_order_ids = []
                    for order_id in self.openOrders:
                        order_found = False
                        for order in relevant_orders:
                            # 确保订单ID比较时类型一致
                            if str(order['id']) == str(order_id):
                                order_found = True
                                # 检查订单状态是否为已成交或部分成交
                                if order['status'] in ['closed', 'filled']:
                                    websocket_filled_orders.append(order)
                                    logger.info(
                                        f"{self.symbolName}websocket检测到订单{order_id}已成交: {order['side']} {order['amount']} @ {order['price']}")
                                break

                        # 如果订单在相关订单中找不到，说明可能已经完全成交并从未成交列表中移除
                        if not order_found:
                            missing_order_ids.append(order_id)
                            logger.info(
                                f"{self.symbolName}订单{order_id}已从websocket更新中消失，可能已完全成交")
                    
                    # 合并websocket检测和主动检查的结果
                    all_filled_orders = websocket_filled_orders + active_check_filled_orders
                    
                    # 去重（避免同一订单被重复处理）
                    unique_filled_orders = []
                    processed_order_ids = set()
                    for order in all_filled_orders:
                        order_id = str(order.get('id', ''))
                        if order_id not in processed_order_ids:
                            unique_filled_orders.append(order)
                            processed_order_ids.add(order_id)

                    # 如果有订单成交或消失，通知tradeManager进行后续处理
                    if unique_filled_orders or missing_order_ids:
                        logger.info(
                            f"{self.symbolName}检测到订单成交，websocket检测: {len(websocket_filled_orders)}个，主动检查: {len(active_check_filled_orders)}个，消失订单: {len(missing_order_ids)}个")
                        # 先停止当前监听，避免重复处理
                        self.inWatchOpenOrder = False
                        self.openOrders = []
                        self.orderWatchStartTime = None
                        # 然后通知tradeManager进行后续处理
                        try:
                            await self.tradeManager.onOrderFilled(unique_filled_orders)
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
