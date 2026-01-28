"""
風險日誌記錄器 (Risk Logger)
記錄風險操作的詳細日誌
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from .risk_classifier import RiskLevel, RiskAssessment
from .sequence_analyzer import SequenceAlert, SequencePattern


class LogLevel(Enum):
    """日誌等級"""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


@dataclass
class RiskLogEntry:
    """風險日誌條目"""
    timestamp: datetime
    log_level: LogLevel
    event_type: str
    command_id: str
    command_name: str
    session_id: Optional[str]
    user_id: Optional[str]
    risk_level: RiskLevel
    risk_score: float
    message: str
    factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'log_level': self.log_level.value,
            'event_type': self.event_type,
            'command_id': self.command_id,
            'command_name': self.command_name,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'risk_level': self.risk_level.name,
            'risk_score': self.risk_score,
            'message': self.message,
            'factors': self.factors,
            'recommendations': self.recommendations,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """轉換為 JSON 字串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RiskLogger:
    """
    風險日誌記錄器
    
    功能：
    1. 記錄所有風險評估結果
    2. 記錄序列警報
    3. 支援多種輸出格式
    4. 提供日誌查詢與分析
    """
    
    def __init__(
        self,
        log_dir: Optional[Union[str, Path]] = None,
        log_file: str = 'moltbot_risk.log',
        json_file: str = 'moltbot_risk.jsonl',
        min_log_level: RiskLevel = RiskLevel.LOW,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_json: bool = True
    ):
        """
        初始化風險日誌記錄器
        
        Args:
            log_dir: 日誌目錄路徑
            log_file: 文字日誌檔名
            json_file: JSON 日誌檔名
            min_log_level: 最低記錄等級
            enable_console: 是否輸出到控制台
            enable_file: 是否寫入文字日誌檔
            enable_json: 是否寫入 JSON 日誌檔
        """
        self.log_dir = Path(log_dir) if log_dir else Path('logs')
        self.log_file = self.log_dir / log_file
        self.json_file = self.log_dir / json_file
        self.min_log_level = min_log_level
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        
        # 記憶體中的日誌緩衝
        self.log_buffer: List[RiskLogEntry] = []
        self.max_buffer_size = 10000
        
        # 設定 Python logging
        self._setup_logging()
        
        # 確保目錄存在
        if enable_file or enable_json:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 風險等級到日誌等級的映射
        self.risk_to_log_level = {
            RiskLevel.CRITICAL: LogLevel.CRITICAL,
            RiskLevel.HIGH: LogLevel.ERROR,
            RiskLevel.MEDIUM: LogLevel.WARNING,
            RiskLevel.LOW: LogLevel.INFO,
            RiskLevel.SAFE: LogLevel.DEBUG,
        }
    
    def _setup_logging(self):
        """設定 Python logging"""
        self.logger = logging.getLogger('moltbot_monitor.risk')
        self.logger.setLevel(logging.DEBUG)
        
        # 清除現有處理器
        self.logger.handlers.clear()
        
        # 格式設定
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台處理器
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 檔案處理器
        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                self.log_file,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def should_log(self, risk_level: RiskLevel) -> bool:
        """檢查是否應該記錄該風險等級"""
        # 風險等級值越小代表風險越高
        return risk_level.value <= self.min_log_level.value
    
    def log_assessment(
        self,
        assessment: RiskAssessment,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        記錄風險評估結果
        
        Args:
            assessment: 風險評估結果
            session_id: 會話 ID
            user_id: 使用者 ID
            metadata: 額外元資料
        """
        if not self.should_log(assessment.profile.level):
            return
        
        log_level = self.risk_to_log_level.get(
            assessment.profile.level, 
            LogLevel.INFO
        )
        
        entry = RiskLogEntry(
            timestamp=datetime.now(),
            log_level=log_level,
            event_type='risk_assessment',
            command_id=assessment.command_id,
            command_name=assessment.command_name,
            session_id=session_id,
            user_id=user_id,
            risk_level=assessment.profile.level,
            risk_score=assessment.final_score,
            message=f"指令 '{assessment.command_name}' 風險評估: {assessment.profile.level.name} (分數: {assessment.final_score:.1f})",
            factors=assessment.factors,
            recommendations=assessment.recommendations,
            metadata=metadata or {}
        )
        
        self._write_log(entry)
    
    def log_sequence_alert(
        self,
        alert: SequenceAlert,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        記錄序列警報
        
        Args:
            alert: 序列警報
            session_id: 會話 ID
            user_id: 使用者 ID
            metadata: 額外元資料
        """
        log_level = self.risk_to_log_level.get(
            alert.severity,
            LogLevel.WARNING
        )
        
        entry = RiskLogEntry(
            timestamp=datetime.now(),
            log_level=log_level,
            event_type='sequence_alert',
            command_id=','.join(alert.commands_involved[:5]),  # 最多5個
            command_name=f"序列: {alert.pattern.name}",
            session_id=session_id,
            user_id=user_id,
            risk_level=alert.severity,
            risk_score=alert.confidence * 100,
            message=f"序列警報: {alert.description}",
            factors=[f"pattern:{alert.pattern.name}", f"confidence:{alert.confidence:.2f}"],
            recommendations=[alert.recommendation],
            metadata={
                'commands_involved': alert.commands_involved,
                **(metadata or {})
            }
        )
        
        self._write_log(entry)
    
    def log_event(
        self,
        event_type: str,
        command_id: str,
        command_name: str,
        risk_level: RiskLevel,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        risk_score: float = 0.0,
        factors: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        記錄通用事件
        
        Args:
            event_type: 事件類型
            command_id: 指令 ID
            command_name: 指令名稱
            risk_level: 風險等級
            message: 日誌訊息
            session_id: 會話 ID
            user_id: 使用者 ID
            risk_score: 風險分數
            factors: 風險因素
            recommendations: 建議
            metadata: 額外元資料
        """
        if not self.should_log(risk_level):
            return
        
        log_level = self.risk_to_log_level.get(risk_level, LogLevel.INFO)
        
        entry = RiskLogEntry(
            timestamp=datetime.now(),
            log_level=log_level,
            event_type=event_type,
            command_id=command_id,
            command_name=command_name,
            session_id=session_id,
            user_id=user_id,
            risk_level=risk_level,
            risk_score=risk_score,
            message=message,
            factors=factors or [],
            recommendations=recommendations or [],
            metadata=metadata or {}
        )
        
        self._write_log(entry)
    
    def _write_log(self, entry: RiskLogEntry):
        """寫入日誌"""
        # 加入緩衝
        self.log_buffer.append(entry)
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer.pop(0)
        
        # 寫入 Python logger
        python_log_level = getattr(logging, entry.log_level.value, logging.INFO)
        self.logger.log(
            python_log_level,
            f"[{entry.event_type}] {entry.command_name} | {entry.risk_level.name} | {entry.message}"
        )
        
        # 寫入 JSON 檔
        if self.enable_json:
            self._append_json(entry)
    
    def _append_json(self, entry: RiskLogEntry):
        """追加 JSON 日誌"""
        try:
            with open(self.json_file, 'a', encoding='utf-8') as f:
                f.write(entry.to_json() + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")
    
    def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        risk_level: Optional[RiskLevel] = None,
        event_type: Optional[str] = None,
        session_id: Optional[str] = None,
        command_name: Optional[str] = None,
        limit: int = 100
    ) -> List[RiskLogEntry]:
        """
        查詢日誌
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            risk_level: 風險等級篩選
            event_type: 事件類型篩選
            session_id: 會話 ID 篩選
            command_name: 指令名稱篩選
            limit: 最大返回數量
            
        Returns:
            List[RiskLogEntry]: 符合條件的日誌條目
        """
        results = []
        
        for entry in reversed(self.log_buffer):
            if len(results) >= limit:
                break
            
            # 時間篩選
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            
            # 風險等級篩選
            if risk_level and entry.risk_level != risk_level:
                continue
            
            # 事件類型篩選
            if event_type and entry.event_type != event_type:
                continue
            
            # 會話 ID 篩選
            if session_id and entry.session_id != session_id:
                continue
            
            # 指令名稱篩選
            if command_name and command_name.lower() not in entry.command_name.lower():
                continue
            
            results.append(entry)
        
        return results
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        取得日誌統計
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            Dict: 統計資訊
        """
        entries = self.log_buffer
        
        # 時間篩選
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        # 統計
        stats = {
            'total_entries': len(entries),
            'by_risk_level': {},
            'by_event_type': {},
            'avg_risk_score': 0.0,
            'high_risk_count': 0,
        }
        
        # 按風險等級統計
        for level in RiskLevel:
            count = len([e for e in entries if e.risk_level == level])
            stats['by_risk_level'][level.name] = count
        
        # 按事件類型統計
        event_types = set(e.event_type for e in entries)
        for event_type in event_types:
            count = len([e for e in entries if e.event_type == event_type])
            stats['by_event_type'][event_type] = count
        
        # 平均風險分數
        if entries:
            stats['avg_risk_score'] = sum(e.risk_score for e in entries) / len(entries)
        
        # 高風險數量 (CRITICAL + HIGH)
        stats['high_risk_count'] = len([
            e for e in entries 
            if e.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH)
        ])
        
        return stats
    
    def export_logs(
        self,
        output_path: Union[str, Path],
        format: str = 'json',
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        匯出日誌
        
        Args:
            output_path: 輸出路徑
            format: 輸出格式 ('json' or 'csv')
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            int: 匯出的條目數量
        """
        entries = self.log_buffer
        
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        output_path = Path(output_path)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(
                    [e.to_dict() for e in entries],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        elif format == 'csv':
            import csv
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                if entries:
                    writer = csv.DictWriter(f, fieldnames=entries[0].to_dict().keys())
                    writer.writeheader()
                    for entry in entries:
                        writer.writerow(entry.to_dict())
        
        return len(entries)
    
    def clear_buffer(self):
        """清除日誌緩衝"""
        self.log_buffer.clear()
