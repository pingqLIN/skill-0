"""
指令序列分析器 (Sequence Analyzer)
分析指令前後搭配的風險，偵測危險的指令組合模式
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import deque
import re

from .risk_classifier import RiskClassifier, RiskLevel, RiskAssessment, RiskProfile


class SequencePattern(Enum):
    """危險序列模式"""
    ESCALATION = auto()          # 權限升級
    DATA_EXFILTRATION = auto()   # 資料外洩
    DESTRUCTIVE_CHAIN = auto()   # 破壞鏈
    BYPASS_ATTEMPT = auto()      # 安全繞過
    RECONNAISSANCE = auto()      # 偵察行為
    PERSISTENCE = auto()         # 持久化攻擊


@dataclass
class CommandContext:
    """指令執行上下文"""
    command_id: str
    command_name: str
    action_types: List[str]
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: str = 'unknown'
    source_ip: Optional[str] = None
    risk_assessment: Optional[RiskAssessment] = None


@dataclass
class SequenceAlert:
    """序列風險警報"""
    pattern: SequencePattern
    severity: RiskLevel
    description: str
    commands_involved: List[str]
    timestamp: datetime
    confidence: float  # 0.0 - 1.0
    recommendation: str


class SequenceAnalyzer:
    """
    指令序列分析器
    
    追蹤並分析連續指令的風險模式
    """
    
    # 危險序列模式定義
    DANGEROUS_PATTERNS: Dict[SequencePattern, Dict] = {
        SequencePattern.ESCALATION: {
            'description': '偵測到可能的權限升級嘗試',
            'trigger_sequence': [
                ['io_read', 'external_call'],  # 讀取配置後呼叫外部
                ['io_read', 'state_change'],   # 讀取後修改狀態
            ],
            'keywords': ['admin', 'privilege', 'sudo', 'root', 'permission'],
            'severity': RiskLevel.CRITICAL,
            'confidence_threshold': 0.7,
        },
        
        SequencePattern.DATA_EXFILTRATION: {
            'description': '偵測到可能的資料外洩行為',
            'trigger_sequence': [
                ['io_read', 'external_call'],     # 讀取後傳送
                ['io_read', 'io_read', 'external_call'],  # 批量讀取後傳送
            ],
            'keywords': ['send', 'transfer', 'upload', 'export', 'extract'],
            'severity': RiskLevel.CRITICAL,
            'confidence_threshold': 0.6,
        },
        
        SequencePattern.DESTRUCTIVE_CHAIN: {
            'description': '偵測到破壞性指令鏈',
            'trigger_sequence': [
                ['io_write', 'io_write'],         # 連續寫入
                ['state_change', 'io_write'],     # 狀態改變後寫入
                ['io_write', 'state_change'],     # 寫入後改變狀態
            ],
            'keywords': ['delete', 'remove', 'drop', 'truncate', 'wipe'],
            'severity': RiskLevel.CRITICAL,
            'confidence_threshold': 0.8,
        },
        
        SequencePattern.BYPASS_ATTEMPT: {
            'description': '偵測到安全機制繞過嘗試',
            'trigger_sequence': [
                ['state_change', 'external_call'],  # 改變狀態後呼叫外部
            ],
            'keywords': ['bypass', 'disable', 'override', 'skip', 'ignore'],
            'severity': RiskLevel.CRITICAL,
            'confidence_threshold': 0.75,
        },
        
        SequencePattern.RECONNAISSANCE: {
            'description': '偵測到偵察行為模式',
            'trigger_sequence': [
                ['io_read', 'io_read', 'io_read'],  # 連續讀取
            ],
            'keywords': ['scan', 'list', 'enumerate', 'discover', 'probe'],
            'severity': RiskLevel.HIGH,
            'confidence_threshold': 0.5,
        },
        
        SequencePattern.PERSISTENCE: {
            'description': '偵測到持久化嘗試',
            'trigger_sequence': [
                ['io_write', 'state_change'],      # 寫入後改變狀態
                ['state_change', 'state_change'],  # 連續狀態改變
            ],
            'keywords': ['install', 'schedule', 'autostart', 'cron', 'startup'],
            'severity': RiskLevel.HIGH,
            'confidence_threshold': 0.6,
        },
    }
    
    def __init__(
        self,
        window_size: int = 10,
        time_window_minutes: int = 5,
        risk_classifier: Optional[RiskClassifier] = None
    ):
        """
        初始化序列分析器
        
        Args:
            window_size: 追蹤的指令數量
            time_window_minutes: 時間窗口（分鐘）
            risk_classifier: 風險分類器實例
        """
        self.window_size = window_size
        self.time_window = timedelta(minutes=time_window_minutes)
        self.risk_classifier = risk_classifier or RiskClassifier()
        
        # 指令歷史緩衝區 (每個 session 獨立)
        self.command_history: Dict[str, deque] = {}
        
        # 已觸發的警報
        self.triggered_alerts: List[SequenceAlert] = []
    
    def add_command(self, context: CommandContext) -> List[SequenceAlert]:
        """
        添加指令到歷史並分析序列
        
        Args:
            context: 指令上下文
            
        Returns:
            List[SequenceAlert]: 觸發的警報列表
        """
        session_id = context.session_id or 'default'
        
        # 初始化 session 歷史
        if session_id not in self.command_history:
            self.command_history[session_id] = deque(maxlen=self.window_size)
        
        # 清理過期指令
        self._cleanup_expired(session_id)
        
        # 添加到歷史
        self.command_history[session_id].append(context)
        
        # 分析序列
        alerts = self._analyze_sequence(session_id)
        
        # 記錄警報
        self.triggered_alerts.extend(alerts)
        
        return alerts
    
    def _cleanup_expired(self, session_id: str):
        """清理過期的指令記錄"""
        if session_id not in self.command_history:
            return
        
        now = datetime.now()
        history = self.command_history[session_id]
        
        # 移除超出時間窗口的指令
        while history and (now - history[0].timestamp) > self.time_window:
            history.popleft()
    
    def _analyze_sequence(self, session_id: str) -> List[SequenceAlert]:
        """分析指令序列"""
        alerts = []
        history = list(self.command_history.get(session_id, []))
        
        if len(history) < 2:
            return alerts
        
        # 提取動作類型序列
        action_sequence = []
        for ctx in history:
            action_sequence.extend(ctx.action_types)
        
        # 提取指令名稱 (用於關鍵字檢測)
        command_names = ' '.join(ctx.command_name for ctx in history).lower()
        
        # 檢查每個危險模式
        for pattern, config in self.DANGEROUS_PATTERNS.items():
            confidence = self._match_pattern(
                action_sequence,
                command_names,
                config
            )
            
            if confidence >= config['confidence_threshold']:
                alert = SequenceAlert(
                    pattern=pattern,
                    severity=config['severity'],
                    description=config['description'],
                    commands_involved=[ctx.command_id for ctx in history],
                    timestamp=datetime.now(),
                    confidence=confidence,
                    recommendation=self._get_recommendation(pattern)
                )
                alerts.append(alert)
        
        return alerts
    
    def _match_pattern(
        self,
        action_sequence: List[str],
        command_names: str,
        config: Dict
    ) -> float:
        """
        匹配危險模式
        
        Returns:
            float: 信心度 (0.0 - 1.0)
        """
        confidence = 0.0
        
        # 檢查動作序列模式
        for trigger_seq in config.get('trigger_sequence', []):
            if self._sequence_contains(action_sequence, trigger_seq):
                confidence = max(confidence, 0.5)
                break
        
        # 檢查關鍵字
        keywords = config.get('keywords', [])
        keyword_matches = sum(1 for kw in keywords if kw in command_names)
        if keyword_matches > 0:
            confidence += min(0.4, keyword_matches * 0.1)
        
        # 檢查序列長度 (越長越可疑)
        if len(action_sequence) >= 5:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _sequence_contains(
        self,
        sequence: List[str],
        pattern: List[str]
    ) -> bool:
        """檢查序列是否包含模式"""
        if len(pattern) > len(sequence):
            return False
        
        # 滑動窗口匹配
        for i in range(len(sequence) - len(pattern) + 1):
            if sequence[i:i + len(pattern)] == pattern:
                return True
        
        return False
    
    def _get_recommendation(self, pattern: SequencePattern) -> str:
        """取得對應模式的處理建議"""
        recommendations = {
            SequencePattern.ESCALATION: '立即中斷操作，審核權限變更',
            SequencePattern.DATA_EXFILTRATION: '暫停外部傳輸，檢查資料敏感性',
            SequencePattern.DESTRUCTIVE_CHAIN: '停止執行，確認操作意圖與備份',
            SequencePattern.BYPASS_ATTEMPT: '阻止操作，報告安全團隊',
            SequencePattern.RECONNAISSANCE: '記錄行為，評估後續操作',
            SequencePattern.PERSISTENCE: '審核系統變更，確認合法性',
        }
        return recommendations.get(pattern, '請謹慎評估後續操作')
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """取得 session 摘要"""
        history = list(self.command_history.get(session_id, []))
        
        if not history:
            return {
                'session_id': session_id,
                'command_count': 0,
                'risk_summary': {},
                'alerts': []
            }
        
        # 統計風險等級分布
        risk_summary = {level.name: 0 for level in RiskLevel}
        for ctx in history:
            if ctx.risk_assessment:
                risk_summary[ctx.risk_assessment.profile.level.name] += 1
        
        # 過濾該 session 的警報
        session_alerts = [
            a for a in self.triggered_alerts
            if any(cmd in a.commands_involved for ctx in history for cmd in [ctx.command_id])
        ]
        
        return {
            'session_id': session_id,
            'command_count': len(history),
            'time_span': str(history[-1].timestamp - history[0].timestamp) if len(history) > 1 else '0',
            'risk_summary': risk_summary,
            'alerts': [
                {
                    'pattern': a.pattern.name,
                    'severity': a.severity.name,
                    'confidence': a.confidence
                }
                for a in session_alerts
            ]
        }
    
    def clear_session(self, session_id: str):
        """清除 session 歷史"""
        if session_id in self.command_history:
            del self.command_history[session_id]
    
    def clear_all(self):
        """清除所有歷史"""
        self.command_history.clear()
        self.triggered_alerts.clear()
