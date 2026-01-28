"""
警報管理器 (Alert Manager)
管理和分發即時警報通知
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime
from enum import Enum, auto
import json
import logging
import threading
from queue import Queue, Empty

from .risk_classifier import RiskLevel


class AlertType(Enum):
    """警報類型"""
    IMMEDIATE = auto()     # 即時警報 (立即危害)
    PRIORITY = auto()      # 優先警報 (高風險)
    STANDARD = auto()      # 標準警報 (中風險)
    INFORMATIONAL = auto() # 資訊性警報 (低風險)


@dataclass
class Alert:
    """警報資料結構"""
    alert_id: str
    alert_type: AlertType
    risk_level: RiskLevel
    title: str
    message: str
    source_command: str
    session_id: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.name,
            'risk_level': self.risk_level.name,
            'title': self.title,
            'message': self.message,
            'source_command': self.source_command,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'metadata': self.metadata
        }


# 警報處理器回呼函數類型
AlertHandler = Callable[[Alert], None]


class AlertManager:
    """
    警報管理器
    
    負責：
    1. 警報生成與分類
    2. 警報分發與通知
    3. 警報狀態追蹤
    4. 警報歷史管理
    """
    
    def __init__(
        self,
        max_history: int = 1000,
        enable_async: bool = True
    ):
        """
        初始化警報管理器
        
        Args:
            max_history: 最大警報歷史數量
            enable_async: 是否啟用異步處理
        """
        self.max_history = max_history
        self.enable_async = enable_async
        
        # 警報歷史
        self.alert_history: List[Alert] = []
        
        # 註冊的處理器 (按類型分類)
        self.handlers: Dict[AlertType, List[AlertHandler]] = {
            alert_type: [] for alert_type in AlertType
        }
        
        # 全域處理器 (處理所有類型)
        self.global_handlers: List[AlertHandler] = []
        
        # 異步處理佇列
        self.alert_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 警報計數器
        self._alert_counter = 0
        self._counter_lock = threading.Lock()
        
        # 設定日誌
        self.logger = logging.getLogger('moltbot_monitor.alerts')
        
        # 風險等級到警報類型的映射
        self.risk_to_alert_type = {
            RiskLevel.CRITICAL: AlertType.IMMEDIATE,
            RiskLevel.HIGH: AlertType.PRIORITY,
            RiskLevel.MEDIUM: AlertType.STANDARD,
            RiskLevel.LOW: AlertType.INFORMATIONAL,
            RiskLevel.SAFE: AlertType.INFORMATIONAL,
        }
        
        # 自動啟動異步處理
        if enable_async:
            self.start_async_processing()
    
    def start_async_processing(self):
        """啟動異步處理線程"""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self._worker_thread.start()
        self.logger.info("Alert async processing started")
    
    def stop_async_processing(self):
        """停止異步處理"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        self.logger.info("Alert async processing stopped")
    
    def _process_queue(self):
        """處理警報佇列"""
        while self._running:
            try:
                alert = self.alert_queue.get(timeout=0.5)
                self._dispatch_alert(alert)
                self.alert_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing alert: {e}")
    
    def _generate_alert_id(self) -> str:
        """生成唯一警報 ID"""
        with self._counter_lock:
            self._alert_counter += 1
            return f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"
    
    def register_handler(
        self,
        handler: AlertHandler,
        alert_types: Optional[List[AlertType]] = None
    ):
        """
        註冊警報處理器
        
        Args:
            handler: 處理器函數
            alert_types: 要處理的警報類型，None 表示所有類型
        """
        if alert_types is None:
            self.global_handlers.append(handler)
            self.logger.info(f"Registered global alert handler: {handler.__name__}")
        else:
            for alert_type in alert_types:
                self.handlers[alert_type].append(handler)
            self.logger.info(f"Registered handler for types: {[t.name for t in alert_types]}")
    
    def unregister_handler(self, handler: AlertHandler):
        """移除警報處理器"""
        # 從全域處理器移除
        if handler in self.global_handlers:
            self.global_handlers.remove(handler)
        
        # 從類型處理器移除
        for alert_type in AlertType:
            if handler in self.handlers[alert_type]:
                self.handlers[alert_type].remove(handler)
    
    def create_alert(
        self,
        risk_level: RiskLevel,
        title: str,
        message: str,
        source_command: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        創建警報
        
        Args:
            risk_level: 風險等級
            title: 警報標題
            message: 警報訊息
            source_command: 來源指令
            session_id: 會話 ID
            metadata: 額外元資料
            
        Returns:
            Alert: 創建的警報物件
        """
        alert_type = self.risk_to_alert_type.get(risk_level, AlertType.STANDARD)
        
        alert = Alert(
            alert_id=self._generate_alert_id(),
            alert_type=alert_type,
            risk_level=risk_level,
            title=title,
            message=message,
            source_command=source_command,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        return alert
    
    def send_alert(self, alert: Alert):
        """
        發送警報
        
        根據警報類型決定處理方式:
        - IMMEDIATE: 同步立即處理
        - 其他: 加入異步佇列
        """
        # 記錄到歷史
        self._add_to_history(alert)
        
        # 根據類型處理
        if alert.alert_type == AlertType.IMMEDIATE or not self.enable_async:
            # 立即處理
            self._dispatch_alert(alert)
        else:
            # 加入佇列
            self.alert_queue.put(alert)
        
        # 記錄日誌
        log_level = logging.CRITICAL if alert.risk_level == RiskLevel.CRITICAL else \
                    logging.WARNING if alert.risk_level == RiskLevel.HIGH else \
                    logging.INFO
        self.logger.log(log_level, f"[{alert.alert_id}] {alert.title}: {alert.message}")
    
    def _dispatch_alert(self, alert: Alert):
        """分發警報到處理器"""
        handlers_called = set()
        
        # 呼叫全域處理器
        for handler in self.global_handlers:
            try:
                handler(alert)
                handlers_called.add(handler.__name__)
            except Exception as e:
                self.logger.error(f"Error in global handler {handler.__name__}: {e}")
        
        # 呼叫類型特定處理器
        for handler in self.handlers.get(alert.alert_type, []):
            try:
                handler(alert)
                handlers_called.add(handler.__name__)
            except Exception as e:
                self.logger.error(f"Error in handler {handler.__name__}: {e}")
        
        if handlers_called:
            self.logger.debug(f"Alert {alert.alert_id} dispatched to: {handlers_called}")
    
    def _add_to_history(self, alert: Alert):
        """添加到警報歷史"""
        self.alert_history.append(alert)
        
        # 清理超出限制的舊警報
        while len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """
        確認警報
        
        Args:
            alert_id: 警報 ID
            acknowledged_by: 確認者
            
        Returns:
            bool: 是否成功
        """
        for alert in self.alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
        return False
    
    def get_unacknowledged_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> List[Alert]:
        """取得未確認的警報"""
        alerts = [a for a in self.alert_history if not a.acknowledged]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if risk_level:
            alerts = [a for a in alerts if a.risk_level == risk_level]
        
        return alerts
    
    def get_alerts_by_session(self, session_id: str) -> List[Alert]:
        """取得特定 session 的警報"""
        return [a for a in self.alert_history if a.session_id == session_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得警報統計"""
        stats = {
            'total_alerts': len(self.alert_history),
            'unacknowledged': len([a for a in self.alert_history if not a.acknowledged]),
            'by_type': {},
            'by_risk_level': {},
            'queue_size': self.alert_queue.qsize() if self.enable_async else 0,
        }
        
        for alert_type in AlertType:
            stats['by_type'][alert_type.name] = len(
                [a for a in self.alert_history if a.alert_type == alert_type]
            )
        
        for risk_level in RiskLevel:
            stats['by_risk_level'][risk_level.name] = len(
                [a for a in self.alert_history if a.risk_level == risk_level]
            )
        
        return stats
    
    def clear_history(self):
        """清除警報歷史"""
        self.alert_history.clear()
        self._alert_counter = 0


# 預設警報處理器範例

def console_alert_handler(alert: Alert):
    """控制台警報處理器"""
    icons = {
        AlertType.IMMEDIATE: '🚨',
        AlertType.PRIORITY: '⚠️',
        AlertType.STANDARD: '📋',
        AlertType.INFORMATIONAL: 'ℹ️',
    }
    
    icon = icons.get(alert.alert_type, '❓')
    print(f"\n{icon} [{alert.alert_type.name}] {alert.title}")
    print(f"   風險等級: {alert.risk_level.name}")
    print(f"   訊息: {alert.message}")
    print(f"   來源: {alert.source_command}")
    print(f"   時間: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   ID: {alert.alert_id}")


def json_alert_handler(alert: Alert):
    """JSON 格式警報處理器 (適用於日誌系統)"""
    print(json.dumps(alert.to_dict(), ensure_ascii=False))
