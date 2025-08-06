# -*- coding: utf-8 -*-
"""
全局配置文件
统一管理系统中的所有配置项
"""


class GlobalConfig:
    """
    全局配置类
    包含系统中所有可配置的参数
    """

    # ========== WebSocket管理器配置 ==========
    class WebSocketConfig:
        """
        WebSocket相关配置
        """
        # 订单监听增强机制配置
        ORDER_CHECK_INTERVAL = 5.0         # 主动检查间隔（秒）
        ORDER_WATCH_TIMEOUT = 30.0         # 订单监听超时时间（秒）

    # ========== 交易管理器配置 ==========
    class TradeConfig:
        """
        交易相关配置
        """
        # 基于成交价的基准价功能
        USE_TRANSACTION_PRICE = True        # 是否使用成交价作为基准价的开关

        # 订单状态监控和恢复机制
        NO_ORDER_TIMEOUT = 60.0            # 无订单超时时间（秒）
        ORDER_CHECK_INTERVAL = 30.0        # 订单检查间隔（秒）

        # 默认交易参数（可被symbols.json中的配置覆盖）
        DEFAULT_BASE_SPREAD = 0.001         # 默认基础价差
        DEFAULT_MIN_SPREAD = 0.0008         # 默认最小价差
        DEFAULT_MAX_SPREAD = 0.003          # 默认最大价差
        DEFAULT_ORDER_COOL_DOWN = 0.1       # 默认下单冷却时间（秒）
        DEFAULT_MAX_STOCK_RATIO = 0.25      # 默认最大持仓比例
        DEFAULT_ORDER_AMOUNT_RATIO = 0.05   # 默认订单金额比例
        DEFAULT_COIN = 'USDT'               # 默认计价币种
        # 默认交易方向：'long'(只做多), 'short'(只做空), 'both'(双向)
        DEFAULT_DIRECTION = 'both'

        # 交易风控参数
        MIN_ORDER_VALUE = 5.5               # 最小订单价值（USDT）
        PRICE_DEVIATION_FACTOR = 0.5        # 价格偏差阈值系数（相对于基础价差）

        # 订单数量动态调整开关
        DYNAMIC_ORDER_AMOUNT = False          # 是否启用动态订单数量调整

        # ========== 价差模式配置 ==========
        # 价差模式：'fixed'(固定价差), 'dynamic'(AS模型动态价差), 'hybrid'(混合模式)
        SPREAD_MODE = 'fixed'                # 默认使用固定价差模式

        # 混合模式阈值配置
        INVENTORY_SAFE_THRESHOLD = 0.4       # 安全库存阈值（低于此值使用固定价差）
        INVENTORY_RISK_THRESHOLD = 0.7       # 风险库存阈值（高于此值使用动态价差）

        # 成本价保护配置
        ENABLE_COST_PROTECTION = True        # 是否启用成本价保护
        MAX_LOSS_RATIO = 0.001              # 最大允许亏损比例（0.1%）
        MIN_PROFIT_RATIO = 0.0005           # 最小利润比例（0.05%）

    # ========== 波动率管理器配置 ==========
    class VolatilityConfig:
        """
        波动率管理器相关配置
        """
        # ATR计算参数
        ATR_PERIOD = 10                     # ATR计算周期
        UPDATE_INTERVAL = 60                # 波动率更新间隔（秒）

        # 波动率倍数参数
        MIN_SPREAD_MULTIPLIER = 1           # minSpread倍数
        BASE_SPREAD_MULTIPLIER = 2          # baseSpread倍数
        MAX_SPREAD_MULTIPLIER = 4          # maxSpread倍数

        # 价差限制参数
        MIN_ALLOWED_SPREAD = 0.0002         # 最小允许价差（0.02%）
        MAX_ALLOWED_SPREAD = 0.1            # 最大允许价差（10%）

        # K线监听参数
        KLINE_TIMEFRAME = '1m'              # K线时间框架
        MAX_KLINE_CACHE = 50                # 最大K线缓存数量

        # 波动率计算参数
        MIN_KLINE_COUNT = 10                # 开始计算波动率的最小K线数量
        VOLATILITY_SMOOTHING = True         # 是否启用波动率平滑
        SMOOTHING_FACTOR = 0.1              # 平滑因子（用于指数移动平均）

    # ========== 数据记录器配置 ==========
    class DataRecorderConfig:
        """
        数据记录相关配置
        """
        # 数据记录间隔和缓存配置
        RECORD_INTERVAL = 60                # 数据记录间隔（秒）
        MAX_CACHE_SIZE = 1000              # 最大缓存大小
        AUTO_FLUSH_INTERVAL = 300          # 自动刷新间隔（秒）

    # ========== 图表管理器配置 ==========
    class ChartConfig:
        """
        图表相关配置
        """
        # 图表更新和显示配置
        CHART_UPDATE_INTERVAL = 30          # 图表更新间隔（秒）
        MAX_DATA_POINTS = 500              # 图表最大数据点数
        CHART_WIDTH = 1200                 # 图表宽度
        CHART_HEIGHT = 600                 # 图表高度

    # ========== 网络和重试配置 ==========
    class NetworkConfig:
        """
        网络相关配置
        """
        # 网络重试配置
        MAX_RETRY_ATTEMPTS = 3             # 最大重试次数
        RETRY_DELAY = 1.0                  # 重试延迟（秒）
        CONNECTION_TIMEOUT = 30.0          # 连接超时时间（秒）
        READ_TIMEOUT = 60.0               # 读取超时时间（秒）

        # WebSocket重连配置
        WS_RECONNECT_DELAY = 5.0          # WebSocket重连延迟（秒）
        WS_MAX_RECONNECT_ATTEMPTS = 10    # WebSocket最大重连次数

    # ========== 日志配置 ==========
    class LogConfig:
        """
        日志相关配置
        """
        # 日志级别和格式配置
        LOG_LEVEL = 'INFO'                 # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
        LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

        # 日志文件配置
        LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 日志文件最大大小（字节）
        LOG_FILE_BACKUP_COUNT = 5          # 日志文件备份数量
        LOG_TO_FILE = True                 # 是否写入文件
        LOG_TO_CONSOLE = True              # 是否输出到控制台

    # ========== 系统配置 ==========
    class SystemConfig:
        """
        系统相关配置
        """
        # 系统运行配置
        GRACEFUL_SHUTDOWN_TIMEOUT = 30.0   # 优雅关闭超时时间（秒）
        TASK_CLEANUP_TIMEOUT = 10.0        # 任务清理超时时间（秒）

        # 内存和性能配置
        MAX_MEMORY_USAGE = 512 * 1024 * 1024  # 最大内存使用量（字节）
        GC_THRESHOLD = 100                 # 垃圾回收阈值

    # ========== 安全配置 ==========
    class SecurityConfig:
        """
        安全相关配置
        """
        # API安全配置
        API_RATE_LIMIT = 100               # API调用频率限制（次/分钟）
        MAX_POSITION_SIZE = 1000000        # 最大持仓大小限制
        MAX_ORDER_SIZE = 100000            # 最大订单大小限制

        # 风险控制配置
        DAILY_LOSS_LIMIT = 0.05            # 日损失限制（比例）
        MAX_DRAWDOWN_LIMIT = 0.10          # 最大回撤限制（比例）


# 配置实例
config = GlobalConfig()

# 便捷访问配置的函数


def get_websocket_config():
    """获取WebSocket配置"""
    return config.WebSocketConfig


def get_trade_config():
    """获取交易配置"""
    return config.TradeConfig


def get_data_recorder_config():
    """获取数据记录器配置"""
    return config.DataRecorderConfig


def get_chart_config():
    """获取图表配置"""
    return config.ChartConfig


def get_network_config():
    """获取网络配置"""
    return config.NetworkConfig


def get_log_config():
    """获取日志配置"""
    return config.LogConfig


def get_system_config():
    """获取系统配置"""
    return config.SystemConfig


def get_security_config():
    """获取安全配置"""
    return config.SecurityConfig


def get_volatility_config():
    """获取波动率配置"""
    return config.VolatilityConfig


# 配置验证函数
def validate_config():
    """
    验证配置的有效性
    """
    errors = []

    # 验证WebSocket配置
    if config.WebSocketConfig.ORDER_CHECK_INTERVAL <= 0:
        errors.append("ORDER_CHECK_INTERVAL必须大于0")

    if config.WebSocketConfig.ORDER_WATCH_TIMEOUT <= 0:
        errors.append("ORDER_WATCH_TIMEOUT必须大于0")

    # 验证交易配置
    if not (0 < config.TradeConfig.DEFAULT_BASE_SPREAD < 1):
        errors.append("DEFAULT_BASE_SPREAD必须在0和1之间")

    if config.TradeConfig.DEFAULT_ORDER_COOL_DOWN < 0:
        errors.append("DEFAULT_ORDER_COOL_DOWN不能为负数")

    if not (0 < config.TradeConfig.DEFAULT_MAX_STOCK_RATIO <= 1):
        errors.append("DEFAULT_MAX_STOCK_RATIO必须在0和1之间")

    # 验证网络配置
    if config.NetworkConfig.MAX_RETRY_ATTEMPTS < 0:
        errors.append("MAX_RETRY_ATTEMPTS不能为负数")

    if config.NetworkConfig.CONNECTION_TIMEOUT <= 0:
        errors.append("CONNECTION_TIMEOUT必须大于0")

    if errors:
        raise ValueError(f"配置验证失败: {'; '.join(errors)}")

    return True


# 配置更新函数
def update_config(section: str, key: str, value):
    """
    动态更新配置项

    Args:
        section: 配置节名称（如 'WebSocketConfig'）
        key: 配置项名称
        value: 新的配置值
    """
    try:
        section_obj = getattr(config, section)
        if hasattr(section_obj, key):
            setattr(section_obj, key, value)
            # 重新验证配置
            validate_config()
            return True
        else:
            raise AttributeError(f"配置项 {key} 在 {section} 中不存在")
    except Exception as e:
        raise ValueError(f"更新配置失败: {e}")


# 配置导出函数
def export_config_to_dict():
    """
    将配置导出为字典格式
    """
    result = {}

    for section_name in ['WebSocketConfig', 'TradeConfig', 'DataRecorderConfig',
                         'ChartConfig', 'NetworkConfig', 'LogConfig',
                         'SystemConfig', 'SecurityConfig']:
        section_obj = getattr(config, section_name)
        section_dict = {}

        for attr_name in dir(section_obj):
            if not attr_name.startswith('_'):
                section_dict[attr_name] = getattr(section_obj, attr_name)

        result[section_name] = section_dict

    return result


# 初始化时验证配置
if __name__ == "__main__":
    try:
        validate_config()
        print("配置验证通过")
    except ValueError as e:
        print(f"配置验证失败: {e}")
