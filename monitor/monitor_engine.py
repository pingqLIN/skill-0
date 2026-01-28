"""
Moltbot 監督引擎 (Monitor Engine)
整合所有監督組件的主要入口點
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import json
from pathlib import Path

from .risk_classifier import RiskClassifier, RiskLevel, RiskAssessment, RiskProfile
from .sequence_analyzer import SequenceAnalyzer, SequenceAlert, CommandContext
from .alert_manager import AlertManager, AlertType, Alert, console_alert_handler
from .risk_logger import RiskLogger


@dataclass
class MonitorConfig:
    """監督器配置"""
    # 風險分類設定
    enable_risk_classification: bool = True
    custom_risk_profiles: Optional[Dict[str, RiskProfile]] = None
    
    # 序列分析設定
    enable_sequence_analysis: bool = True
    sequence_window_size: int = 10
    sequence_time_window_minutes: int = 5
    
    # 警報設定
    enable_alerts: bool = True
    alert_threshold_level: RiskLevel = RiskLevel.HIGH  # 觸發警報的最低風險等級
    enable_async_alerts: bool = True
    
    # 日誌設定
    enable_logging: bool = True
    log_directory: Optional[str] = None
    min_log_level: RiskLevel = RiskLevel.LOW
    enable_console_log: bool = True
    enable_file_log: bool = True
    enable_json_log: bool = True


@dataclass
class CommandInput:
    """指令輸入資料"""
    command_id: str
    command_name: str
    actions: List[Dict[str, Any]]
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    environment: str = 'development'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitorResult:
    """監督結果"""
    command_id: str
    command_name: str
    timestamp: datetime
    risk_assessment: Optional[RiskAssessment] = None
    sequence_alerts: List[SequenceAlert] = field(default_factory=list)
    alerts_sent: List[Alert] = field(default_factory=list)
    blocked: bool = False
    block_reason: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_safe(self) -> bool:
        """判斷是否安全"""
        if self.blocked:
            return False
        if self.risk_assessment:
            return self.risk_assessment.profile.level.value >= RiskLevel.MEDIUM.value
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'command_id': self.command_id,
            'command_name': self.command_name,
            'timestamp': self.timestamp.isoformat(),
            'risk_assessment': {
                'level': self.risk_assessment.profile.level.name,
                'score': self.risk_assessment.final_score,
                'factors': self.risk_assessment.factors,
            } if self.risk_assessment else None,
            'sequence_alerts': [
                {
                    'pattern': a.pattern.name,
                    'severity': a.severity.name,
                    'confidence': a.confidence,
                }
                for a in self.sequence_alerts
            ],
            'alerts_sent': len(self.alerts_sent),
            'blocked': self.blocked,
            'block_reason': self.block_reason,
            'is_safe': self.is_safe,
            'recommendations': self.recommendations,
        }


class MoltbotMonitor:
    """
    Moltbot 監督引擎
    
    這是 Moltbot 擴充監督程式的主要入口點。
    整合風險分類、序列分析、警報管理和日誌記錄功能。
    
    使用範例:
    
    ```python
    from monitor import MoltbotMonitor, MonitorConfig, CommandInput
    
    # 建立監督器
    config = MonitorConfig(
        alert_threshold_level=RiskLevel.HIGH,
        enable_console_log=True
    )
    monitor = MoltbotMonitor(config)
    
    # 監督指令
    command = CommandInput(
        command_id='cmd_001',
        command_name='delete_files',
        actions=[
            {'action_type': 'io_write', 'name': 'Delete', 'description': 'Delete all temp files'}
        ],
        session_id='session_123'
    )
    
    result = monitor.check_command(command)
    
    if not result.is_safe:
        print(f"危險: {result.block_reason}")
    ```
    """
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        """
        初始化監督引擎
        
        Args:
            config: 監督器配置
        """
        self.config = config or MonitorConfig()
        
        # 初始化組件
        self.risk_classifier: Optional[RiskClassifier] = None
        self.sequence_analyzer: Optional[SequenceAnalyzer] = None
        self.alert_manager: Optional[AlertManager] = None
        self.risk_logger: Optional[RiskLogger] = None
        
        self._initialize_components()
        
        # 統計
        self._stats = {
            'total_checked': 0,
            'blocked': 0,
            'alerts_sent': 0,
            'by_risk_level': {level.name: 0 for level in RiskLevel},
        }
        
        # 自訂回呼
        self._pre_check_callbacks: List[Callable[[CommandInput], None]] = []
        self._post_check_callbacks: List[Callable[[MonitorResult], None]] = []
    
    def _initialize_components(self):
        """初始化各組件"""
        # 風險分類器
        if self.config.enable_risk_classification:
            self.risk_classifier = RiskClassifier(
                custom_profiles=self.config.custom_risk_profiles
            )
        
        # 序列分析器
        if self.config.enable_sequence_analysis:
            self.sequence_analyzer = SequenceAnalyzer(
                window_size=self.config.sequence_window_size,
                time_window_minutes=self.config.sequence_time_window_minutes,
                risk_classifier=self.risk_classifier
            )
        
        # 警報管理器
        if self.config.enable_alerts:
            self.alert_manager = AlertManager(
                enable_async=self.config.enable_async_alerts
            )
            # 註冊預設處理器
            if self.config.enable_console_log:
                self.alert_manager.register_handler(
                    console_alert_handler,
                    alert_types=[AlertType.IMMEDIATE, AlertType.PRIORITY]
                )
        
        # 風險日誌
        if self.config.enable_logging:
            self.risk_logger = RiskLogger(
                log_dir=self.config.log_directory,
                min_log_level=self.config.min_log_level,
                enable_console=self.config.enable_console_log,
                enable_file=self.config.enable_file_log,
                enable_json=self.config.enable_json_log
            )
    
    def check_command(self, command: CommandInput) -> MonitorResult:
        """
        檢查指令風險
        
        這是主要的監督入口點。對每個要執行的指令進行：
        1. 風險評估
        2. 序列分析
        3. 警報觸發
        4. 日誌記錄
        
        Args:
            command: 指令輸入資料
            
        Returns:
            MonitorResult: 監督結果
        """
        # 執行前置回呼
        for callback in self._pre_check_callbacks:
            try:
                callback(command)
            except Exception:
                pass
        
        result = MonitorResult(
            command_id=command.command_id,
            command_name=command.command_name,
            timestamp=datetime.now()
        )
        
        # 1. 風險評估
        if self.risk_classifier:
            result.risk_assessment = self.risk_classifier.assess_command(
                command_id=command.command_id,
                command_name=command.command_name,
                actions=command.actions,
                context={
                    'environment': command.environment,
                    **command.metadata
                }
            )
            
            # 收集建議
            result.recommendations.extend(result.risk_assessment.recommendations)
            
            # 更新統計
            self._stats['by_risk_level'][result.risk_assessment.profile.level.name] += 1
            
            # 記錄日誌
            if self.risk_logger:
                self.risk_logger.log_assessment(
                    result.risk_assessment,
                    session_id=command.session_id,
                    user_id=command.user_id,
                    metadata=command.metadata
                )
        
        # 2. 序列分析
        if self.sequence_analyzer and result.risk_assessment:
            context = CommandContext(
                command_id=command.command_id,
                command_name=command.command_name,
                action_types=[a.get('action_type', 'unknown') for a in command.actions],
                timestamp=datetime.now(),
                user_id=command.user_id,
                session_id=command.session_id,
                environment=command.environment,
                risk_assessment=result.risk_assessment
            )
            
            result.sequence_alerts = self.sequence_analyzer.add_command(context)
            
            # 記錄序列警報
            if self.risk_logger:
                for alert in result.sequence_alerts:
                    self.risk_logger.log_sequence_alert(
                        alert,
                        session_id=command.session_id,
                        user_id=command.user_id
                    )
        
        # 3. 決定是否阻擋
        should_block, block_reason = self._should_block(result)
        if should_block:
            result.blocked = True
            result.block_reason = block_reason
            self._stats['blocked'] += 1
        
        # 4. 發送警報
        if self.alert_manager:
            alerts = self._create_alerts(command, result)
            for alert in alerts:
                self.alert_manager.send_alert(alert)
            result.alerts_sent = alerts
            self._stats['alerts_sent'] += len(alerts)
        
        # 更新統計
        self._stats['total_checked'] += 1
        
        # 執行後置回呼
        for callback in self._post_check_callbacks:
            try:
                callback(result)
            except Exception:
                pass
        
        return result
    
    def _should_block(self, result: MonitorResult) -> tuple:
        """判斷是否應該阻擋指令"""
        # 檢查風險評估
        if result.risk_assessment:
            level = result.risk_assessment.profile.level
            
            # CRITICAL 直接阻擋
            if level == RiskLevel.CRITICAL:
                return True, f"危險操作: {result.risk_assessment.profile.description}"
        
        # 檢查序列警報
        for alert in result.sequence_alerts:
            if alert.severity == RiskLevel.CRITICAL and alert.confidence >= 0.8:
                return True, f"危險序列模式: {alert.description}"
        
        return False, None
    
    def _create_alerts(self, command: CommandInput, result: MonitorResult) -> List[Alert]:
        """根據結果創建警報"""
        alerts = []
        
        if not self.alert_manager:
            return alerts
        
        # 風險評估警報
        if result.risk_assessment:
            level = result.risk_assessment.profile.level
            
            # 只對達到閾值的風險發送警報
            if level.value <= self.config.alert_threshold_level.value:
                alert = self.alert_manager.create_alert(
                    risk_level=level,
                    title=f"風險指令偵測: {command.command_name}",
                    message=f"風險分數: {result.risk_assessment.final_score:.1f}, "
                            f"風險等級: {level.name}",
                    source_command=command.command_id,
                    session_id=command.session_id,
                    metadata={
                        'factors': result.risk_assessment.factors,
                        'user_id': command.user_id,
                    }
                )
                alerts.append(alert)
        
        # 序列警報
        for seq_alert in result.sequence_alerts:
            alert = self.alert_manager.create_alert(
                risk_level=seq_alert.severity,
                title=f"序列警報: {seq_alert.pattern.name}",
                message=seq_alert.description,
                source_command=command.command_id,
                session_id=command.session_id,
                metadata={
                    'pattern': seq_alert.pattern.name,
                    'confidence': seq_alert.confidence,
                    'commands_involved': seq_alert.commands_involved,
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def register_pre_check_callback(self, callback: Callable[[CommandInput], None]):
        """註冊檢查前回呼"""
        self._pre_check_callbacks.append(callback)
    
    def register_post_check_callback(self, callback: Callable[[MonitorResult], None]):
        """註冊檢查後回呼"""
        self._post_check_callbacks.append(callback)
    
    def register_alert_handler(
        self,
        handler: Callable[[Alert], None],
        alert_types: Optional[List[AlertType]] = None
    ):
        """註冊警報處理器"""
        if self.alert_manager:
            self.alert_manager.register_handler(handler, alert_types)
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """取得 session 摘要"""
        summary = {
            'session_id': session_id,
            'sequence_summary': None,
            'alerts': [],
            'log_entries': [],
        }
        
        if self.sequence_analyzer:
            summary['sequence_summary'] = self.sequence_analyzer.get_session_summary(session_id)
        
        if self.alert_manager:
            summary['alerts'] = [
                a.to_dict() 
                for a in self.alert_manager.get_alerts_by_session(session_id)
            ]
        
        if self.risk_logger:
            entries = self.risk_logger.query_logs(session_id=session_id, limit=50)
            summary['log_entries'] = [e.to_dict() for e in entries]
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得監督統計"""
        stats = {
            'monitor_stats': self._stats.copy(),
        }
        
        if self.alert_manager:
            stats['alert_stats'] = self.alert_manager.get_statistics()
        
        if self.risk_logger:
            stats['log_stats'] = self.risk_logger.get_statistics()
        
        return stats
    
    def clear_session(self, session_id: str):
        """清除 session 資料"""
        if self.sequence_analyzer:
            self.sequence_analyzer.clear_session(session_id)
    
    def shutdown(self):
        """關閉監督器"""
        if self.alert_manager:
            self.alert_manager.stop_async_processing()


# 便捷函數

def create_monitor(
    alert_threshold: RiskLevel = RiskLevel.HIGH,
    enable_console: bool = True,
    log_dir: Optional[str] = None
) -> MoltbotMonitor:
    """
    建立監督器的便捷函數
    
    Args:
        alert_threshold: 警報閾值
        enable_console: 是否啟用控制台輸出
        log_dir: 日誌目錄
        
    Returns:
        MoltbotMonitor: 配置好的監督器
    """
    config = MonitorConfig(
        alert_threshold_level=alert_threshold,
        enable_console_log=enable_console,
        log_directory=log_dir
    )
    return MoltbotMonitor(config)
