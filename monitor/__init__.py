"""
Moltbot Monitor Extension
基於 Skill-0 篩選器技術的即時監督程序

提供以下功能：
1. 指令風險評估 (Risk Assessment)
2. 指令序列分析 (Command Sequence Analysis)
3. 即時警報通知 (Real-time Alerts)
4. 風險操作日誌 (Risk Logging)
"""

from .risk_classifier import RiskClassifier, RiskLevel
from .sequence_analyzer import SequenceAnalyzer, CommandContext
from .alert_manager import AlertManager, AlertType, Alert
from .risk_logger import RiskLogger
from .monitor_engine import MoltbotMonitor, MonitorConfig, CommandInput, create_monitor

__all__ = [
    'MoltbotMonitor',
    'MonitorConfig',
    'CommandInput',
    'create_monitor',
    'RiskClassifier',
    'RiskLevel',
    'SequenceAnalyzer',
    'CommandContext',
    'AlertManager',
    'AlertType',
    'Alert',
    'RiskLogger'
]

__version__ = '1.0.0'
