import matplotlib
matplotlib.use('TkAgg')  # 设置后端
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.dates import DateFormatter
import numpy as np
from datetime import datetime
import threading
import time
import queue
from typing import Dict, List
from util.sLogger import logger
from core.dataRecorder import data_recorder

class ChartManager:
    """图表管理器 - 使用非阻塞方式显示实时图表"""
    
    def __init__(self, update_interval=3000):  # 更新间隔3秒，减少频率
        self.update_interval = update_interval
        self.running = False
        self.fig = None
        self.axes = None
        self.lines = {}
        self.text_labels = {}  # 存储文本标签引用
        self.animation = None
        self.last_data_count = 0  # 记录上次数据数量，避免不必要的重绘
        
        # 设置matplotlib中文字体和交互模式
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['figure.dpi'] = 100  # 设置合适的DPI
        plt.ion()  # 开启交互模式
        
        logger.info("图表管理器初始化完成")
    
    def start_charts(self):
        """启动图表显示"""
        if self.running:
            logger.warning("图表已在运行中")
            return
        
        try:
            self.running = True
            
            # 创建图表窗口 - 调整为适合4K显示器的尺寸
            self.fig, self.axes = plt.subplots(2, 1, figsize=(10, 8))
            self.fig.suptitle('GLFT网格交易实时监控', fontsize=14, fontweight='bold')
            
            # 设置窗口位置和大小
            mngr = self.fig.canvas.manager
            mngr.window.wm_geometry("+100+100")  # 设置窗口位置
            
            # 设置子图
            self._setup_subplots()
            
            # 创建动画
            self.animation = animation.FuncAnimation(
                self.fig, 
                self._update_charts, 
                interval=self.update_interval,
                blit=False,
                cache_frame_data=False
            )
            
            # 显示图表
            plt.tight_layout()
            plt.show(block=False)  # 非阻塞显示
            plt.pause(0.1)  # 短暂暂停以确保窗口显示
            
            logger.info("图表已启动")
            
        except Exception as e:
            logger.error(f"启动图表时出错: {e}")
            self.running = False
    
    def stop_charts(self):
        """停止图表显示"""
        self.running = False
        try:
            if self.animation:
                self.animation.event_source.stop()
            if self.fig:
                plt.close(self.fig)
            plt.ioff()  # 关闭交互模式
            logger.info("图表已停止")
        except Exception as e:
            logger.error(f"停止图表时出错: {e}")
    
    def update_display(self):
        """手动更新显示（用于非动画模式）"""
        if self.fig and self.running:
            try:
                plt.pause(0.01)  # 短暂暂停以更新显示
            except Exception as e:
                logger.error(f"更新显示时出错: {e}")
    
    def _setup_subplots(self):
        """设置子图"""
        # 第一个子图：账户权益相关
        ax1 = self.axes[0]
        ax1.set_title('账户权益监控', fontsize=12, fontweight='bold')
        ax1.set_xlabel('时间', fontsize=10)
        ax1.set_ylabel('USDT', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(labelsize=9)
        
        # 第二个子图：成交量
        ax2 = self.axes[1]
        ax2.set_title('累计成交量', fontsize=12, fontweight='bold')
        ax2.set_xlabel('时间', fontsize=10)
        ax2.set_ylabel('成交量', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(labelsize=9)
        
        # 初始化线条
        self.lines['equity'], = ax1.plot([], [], 'b-', linewidth=1.5, label='账户权益', alpha=0.8)
        self.lines['total_fee'], = ax1.plot([], [], 'r-', linewidth=1.5, label='累计手续费', alpha=0.8)
        self.lines['equity_plus_half_fee'], = ax1.plot([], [], 'g-', linewidth=1.5, label='权益+50%手续费', alpha=0.8)
        self.lines['volume'], = ax2.plot([], [], 'm-', linewidth=1.5, label='累计成交量', alpha=0.8)
        
        # 设置图例
        ax1.legend(loc='upper left', fontsize=9)
        ax2.legend(loc='upper left', fontsize=9)
        
        # 初始化文本标签（避免重复创建）
        self.text_labels['equity'] = ax1.text(0.02, 0.98, '', transform=ax1.transAxes, 
                                            fontsize=9, verticalalignment='top',
                                            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        self.text_labels['fee'] = ax1.text(0.02, 0.90, '', transform=ax1.transAxes, 
                                         fontsize=9, verticalalignment='top',
                                         bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
        self.text_labels['equity_plus_fee'] = ax1.text(0.02, 0.82, '', transform=ax1.transAxes, 
                                                      fontsize=9, verticalalignment='top',
                                                      bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        self.text_labels['volume'] = ax2.text(0.02, 0.98, '', transform=ax2.transAxes, 
                                             fontsize=9, verticalalignment='top',
                                             bbox=dict(boxstyle='round', facecolor='plum', alpha=0.8))
    
    def _update_charts(self, frame):
        """更新图表数据 - 优化性能版本"""
        if not self.running:
            return
        
        try:
            # 获取数据
            account_data = data_recorder.get_account_data()
            
            if not account_data['timestamps']:
                return
            
            # 检查数据是否有变化，避免不必要的重绘
            current_data_count = len(account_data['timestamps'])
            if current_data_count == self.last_data_count and current_data_count > 0:
                return
            
            self.last_data_count = current_data_count
            
            # 转换时间戳为datetime对象
            timestamps = [datetime.fromtimestamp(ts) for ts in account_data['timestamps']]
            
            # 更新线条数据
            self.lines['equity'].set_data(timestamps, account_data['equity'])
            self.lines['total_fee'].set_data(timestamps, account_data['total_fee'])
            self.lines['equity_plus_half_fee'].set_data(timestamps, account_data['equity_plus_half_fee'])
            self.lines['volume'].set_data(timestamps, account_data['total_volume'])
            
            # 只在有足够数据时才调整坐标轴（减少频繁调整）
            if len(timestamps) > 5:
                for ax in self.axes:
                    ax.relim()
                    ax.autoscale_view(tight=True)
            
            # 优化时间轴格式化（减少频率）
            if len(timestamps) > 1 and current_data_count % 5 == 0:  # 每5次更新才格式化一次
                time_span = timestamps[-1] - timestamps[0]
                if time_span.total_seconds() < 3600:  # 小于1小时
                    date_format = DateFormatter('%H:%M:%S')
                elif time_span.total_seconds() < 86400:  # 小于1天
                    date_format = DateFormatter('%H:%M')
                else:
                    date_format = DateFormatter('%m-%d %H:%M')
                
                for ax in self.axes:
                    ax.xaxis.set_major_formatter(date_format)
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, fontsize=8)
            
            # 更新图表标题
            summary = data_recorder.get_summary()
            title_text = f'GLFT网格交易实时监控 - 权益: {summary["current_equity"]:.2f} USDT | 总手续费: {summary["total_fee"]:.4f} USDT | 总成交量: {summary["total_volume"]:.2f}'
            self.fig.suptitle(title_text, fontsize=11)
            
            # 更新文本标签（使用预创建的标签，避免重复创建）
            if account_data['equity']:
                latest_equity = account_data['equity'][-1]
                latest_fee = account_data['total_fee'][-1]
                latest_equity_plus_half_fee = account_data['equity_plus_half_fee'][-1]
                latest_volume = account_data['total_volume'][-1]
                
                # 更新文本内容而不是重新创建
                self.text_labels['equity'].set_text(f'当前权益: {latest_equity:.2f} USDT')
                self.text_labels['fee'].set_text(f'累计手续费: {latest_fee:.4f} USDT')
                self.text_labels['equity_plus_fee'].set_text(f'权益+50%手续费: {latest_equity_plus_half_fee:.2f} USDT')
                self.text_labels['volume'].set_text(f'累计成交量: {latest_volume:.2f}')
            
        except Exception as e:
            logger.error(f"更新图表时出错: {e}")
    
    def save_chart(self, filename=None):
        """保存当前图表"""
        if self.fig is None:
            logger.warning("图表未初始化，无法保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trading_chart_{timestamp}.png'
        
        try:
            self.fig.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存为: {filename}")
        except Exception as e:
            logger.error(f"保存图表失败: {e}")

# 全局图表管理器实例
chart_manager = ChartManager()