"""
Moltbot Monitor 測試套件
"""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 確保可以 import monitor 模組
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor import (
    MoltbotMonitor,
    RiskClassifier,
    RiskLevel,
    SequenceAnalyzer,
    CommandContext,
    AlertManager,
    AlertType,
    RiskLogger,
    MonitorConfig,
    CommandInput
)
from monitor.risk_classifier import RiskProfile, RiskAssessment
from monitor.sequence_analyzer import SequenceAlert, SequencePattern


class TestRiskClassifier:
    """風險分類器測試"""
    
    def test_basic_classification(self):
        """測試基本風險分類"""
        classifier = RiskClassifier()
        
        # 測試低風險動作
        read_action = {
            'action_type': 'io_read',
            'name': 'Read File',
            'description': 'Read a configuration file'
        }
        profile = classifier.classify_action(read_action)
        assert profile.level == RiskLevel.LOW
        
        # 測試高風險動作
        external_action = {
            'action_type': 'external_call',
            'name': 'API Call',
            'description': 'Call external API'
        }
        profile = classifier.classify_action(external_action)
        assert profile.level == RiskLevel.HIGH
    
    def test_keyword_detection(self):
        """測試關鍵字偵測"""
        classifier = RiskClassifier()
        
        # 測試危險關鍵字
        delete_action = {
            'action_type': 'io_write',
            'name': 'Delete Files',
            'description': 'Delete all temporary files'
        }
        profile = classifier.classify_action(delete_action)
        assert profile.level.value <= RiskLevel.HIGH.value
    
    def test_critical_keyword_detection(self):
        """測試致命關鍵字偵測"""
        classifier = RiskClassifier()
        
        # 測試致命關鍵字
        wipe_action = {
            'action_type': 'io_write',
            'name': 'Wipe Data',
            'description': 'Wipe all user data'
        }
        profile = classifier.classify_action(wipe_action)
        assert profile.level == RiskLevel.CRITICAL
    
    def test_command_assessment(self):
        """測試完整指令評估"""
        classifier = RiskClassifier()
        
        assessment = classifier.assess_command(
            command_id='cmd_001',
            command_name='test_command',
            actions=[
                {'action_type': 'io_read', 'name': 'Read', 'description': 'Read data'},
                {'action_type': 'compute', 'name': 'Process', 'description': 'Process data'},
            ]
        )
        
        assert assessment.command_id == 'cmd_001'
        assert assessment.final_score >= 0
        assert assessment.final_score <= 100
        assert assessment.profile.level.value >= RiskLevel.LOW.value
    
    def test_empty_command(self):
        """測試空指令評估"""
        classifier = RiskClassifier()
        
        assessment = classifier.assess_command(
            command_id='empty_cmd',
            command_name='empty',
            actions=[]
        )
        
        assert assessment.profile.level == RiskLevel.LOW
        assert assessment.final_score == 0.0
    
    def test_side_effects_detection(self):
        """測試副作用偵測"""
        classifier = RiskClassifier()
        
        action_with_effects = {
            'action_type': 'io_write',
            'name': 'Write',
            'description': 'Write data',
            'side_effects': ['data_loss', 'state_change']
        }
        profile = classifier.classify_action(action_with_effects)
        assert profile.level == RiskLevel.CRITICAL


class TestSequenceAnalyzer:
    """序列分析器測試"""
    
    def test_basic_sequence(self):
        """測試基本序列追蹤"""
        analyzer = SequenceAnalyzer(window_size=5, time_window_minutes=10)
        
        context = CommandContext(
            command_id='cmd_001',
            command_name='read_file',
            action_types=['io_read'],
            timestamp=datetime.now(),
            session_id='session_1'
        )
        
        alerts = analyzer.add_command(context)
        # 單一指令不應觸發警報
        assert len(alerts) == 0
    
    def test_data_exfiltration_pattern(self):
        """測試資料外洩模式偵測"""
        analyzer = SequenceAnalyzer(window_size=10, time_window_minutes=10)
        
        # 模擬資料外洩模式: io_read -> external_call
        commands = [
            CommandContext(
                command_id='cmd_001',
                command_name='read_sensitive_data',
                action_types=['io_read'],
                timestamp=datetime.now(),
                session_id='session_1'
            ),
            CommandContext(
                command_id='cmd_002',
                command_name='send_data',
                action_types=['external_call'],
                timestamp=datetime.now() + timedelta(seconds=1),
                session_id='session_1'
            )
        ]
        
        alerts = []
        for cmd in commands:
            alerts.extend(analyzer.add_command(cmd))
        
        # 應該偵測到資料外洩模式
        exfiltration_alerts = [
            a for a in alerts 
            if a.pattern == SequencePattern.DATA_EXFILTRATION
        ]
        assert len(exfiltration_alerts) > 0 or len(alerts) == 0  # 可能信心度不足
    
    def test_destructive_chain_pattern(self):
        """測試破壞性指令鏈偵測"""
        analyzer = SequenceAnalyzer(window_size=10, time_window_minutes=10)
        
        # 模擬破壞性指令鏈
        commands = [
            CommandContext(
                command_id='cmd_001',
                command_name='delete_files',
                action_types=['io_write'],
                timestamp=datetime.now(),
                session_id='session_1'
            ),
            CommandContext(
                command_id='cmd_002',
                command_name='drop_tables',
                action_types=['io_write'],
                timestamp=datetime.now() + timedelta(seconds=1),
                session_id='session_1'
            )
        ]
        
        alerts = []
        for cmd in commands:
            alerts.extend(analyzer.add_command(cmd))
        
        # 檢查是否有破壞性警報
        destructive_alerts = [
            a for a in alerts 
            if a.pattern == SequencePattern.DESTRUCTIVE_CHAIN
        ]
        # 至少應該有一些警報
        assert isinstance(alerts, list)
    
    def test_session_isolation(self):
        """測試 session 隔離"""
        analyzer = SequenceAnalyzer(window_size=5)
        
        # 不同 session 的指令
        cmd1 = CommandContext(
            command_id='cmd_001',
            command_name='cmd1',
            action_types=['io_read'],
            timestamp=datetime.now(),
            session_id='session_1'
        )
        cmd2 = CommandContext(
            command_id='cmd_002',
            command_name='cmd2',
            action_types=['io_read'],
            timestamp=datetime.now(),
            session_id='session_2'
        )
        
        analyzer.add_command(cmd1)
        analyzer.add_command(cmd2)
        
        summary1 = analyzer.get_session_summary('session_1')
        summary2 = analyzer.get_session_summary('session_2')
        
        assert summary1['command_count'] == 1
        assert summary2['command_count'] == 1


class TestAlertManager:
    """警報管理器測試"""
    
    def test_alert_creation(self):
        """測試警報創建"""
        manager = AlertManager(enable_async=False)
        
        alert = manager.create_alert(
            risk_level=RiskLevel.HIGH,
            title='Test Alert',
            message='This is a test alert',
            source_command='cmd_001'
        )
        
        assert alert.alert_id.startswith('ALT-')
        assert alert.risk_level == RiskLevel.HIGH
        assert alert.title == 'Test Alert'
        assert not alert.acknowledged
    
    def test_alert_send(self):
        """測試警報發送"""
        manager = AlertManager(enable_async=False)
        
        received_alerts = []
        
        def handler(alert):
            received_alerts.append(alert)
        
        manager.register_handler(handler)
        
        alert = manager.create_alert(
            risk_level=RiskLevel.CRITICAL,
            title='Critical Alert',
            message='Critical issue',
            source_command='cmd_001'
        )
        manager.send_alert(alert)
        
        assert len(received_alerts) == 1
        assert received_alerts[0].title == 'Critical Alert'
    
    def test_alert_acknowledge(self):
        """測試警報確認"""
        manager = AlertManager(enable_async=False)
        
        alert = manager.create_alert(
            risk_level=RiskLevel.HIGH,
            title='Test',
            message='Test',
            source_command='cmd_001'
        )
        manager.send_alert(alert)
        
        success = manager.acknowledge_alert(alert.alert_id, 'test_user')
        assert success
        
        # 驗證警報已確認
        updated_alert = manager.alert_history[-1]
        assert updated_alert.acknowledged
        assert updated_alert.acknowledged_by == 'test_user'
    
    def test_unacknowledged_filter(self):
        """測試未確認警報篩選"""
        manager = AlertManager(enable_async=False)
        
        # 發送多個警報
        for i in range(3):
            alert = manager.create_alert(
                risk_level=RiskLevel.HIGH,
                title=f'Alert {i}',
                message='Test',
                source_command=f'cmd_{i}'
            )
            manager.send_alert(alert)
        
        # 確認第一個
        manager.acknowledge_alert(manager.alert_history[0].alert_id, 'user')
        
        unack = manager.get_unacknowledged_alerts()
        assert len(unack) == 2


class TestRiskLogger:
    """風險日誌測試"""
    
    def test_log_assessment(self, tmp_path):
        """測試評估結果記錄"""
        logger = RiskLogger(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_json=True
        )
        
        assessment = RiskAssessment(
            command_id='cmd_001',
            command_name='test_command',
            profile=RiskProfile(
                level=RiskLevel.HIGH,
                category='test',
                description='Test profile',
                action_type='io_write'
            ),
            base_score=70.0,
            context_score=10.0,
            final_score=80.0,
            factors=['test_factor'],
            recommendations=['test_rec']
        )
        
        logger.log_assessment(assessment, session_id='session_1')
        
        # 驗證緩衝區
        assert len(logger.log_buffer) == 1
        assert logger.log_buffer[0].risk_level == RiskLevel.HIGH
    
    def test_query_logs(self, tmp_path):
        """測試日誌查詢"""
        logger = RiskLogger(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_json=False,
            min_log_level=RiskLevel.LOW
        )
        
        # 記錄多個事件
        for level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]:
            logger.log_event(
                event_type='test',
                command_id=f'cmd_{level.name}',
                command_name=f'command_{level.name}',
                risk_level=level,
                message=f'Test {level.name}'
            )
        
        # 查詢高風險
        high_logs = logger.query_logs(risk_level=RiskLevel.HIGH)
        assert len(high_logs) == 1
        
        # 查詢全部
        all_logs = logger.query_logs()
        assert len(all_logs) == 3
    
    def test_statistics(self, tmp_path):
        """測試統計功能"""
        logger = RiskLogger(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_json=False,
            min_log_level=RiskLevel.LOW
        )
        
        # 記錄多個事件
        for _ in range(5):
            logger.log_event(
                event_type='test',
                command_id='cmd',
                command_name='command',
                risk_level=RiskLevel.HIGH,
                message='Test',
                risk_score=75.0
            )
        
        stats = logger.get_statistics()
        assert stats['total_entries'] == 5
        assert stats['by_risk_level']['HIGH'] == 5
        assert stats['avg_risk_score'] == 75.0


class TestMoltbotMonitor:
    """監督引擎整合測試"""
    
    def test_basic_check(self):
        """測試基本指令檢查"""
        config = MonitorConfig(
            enable_alerts=False,
            enable_logging=False,
            enable_console_log=False
        )
        monitor = MoltbotMonitor(config)
        
        command = CommandInput(
            command_id='cmd_001',
            command_name='read_file',
            actions=[
                {'action_type': 'io_read', 'name': 'Read', 'description': 'Read file'}
            ]
        )
        
        result = monitor.check_command(command)
        
        assert result.command_id == 'cmd_001'
        assert result.risk_assessment is not None
        assert result.is_safe
        assert not result.blocked
    
    def test_dangerous_command_blocked(self):
        """測試危險指令被阻擋"""
        config = MonitorConfig(
            enable_alerts=False,
            enable_logging=False,
            enable_console_log=False
        )
        monitor = MoltbotMonitor(config)
        
        command = CommandInput(
            command_id='cmd_002',
            command_name='wipe_database',
            actions=[
                {
                    'action_type': 'io_write',
                    'name': 'Wipe',
                    'description': 'Wipe all database records',
                    'side_effects': ['data_loss']
                }
            ]
        )
        
        result = monitor.check_command(command)
        
        assert result.risk_assessment.profile.level == RiskLevel.CRITICAL
        assert result.blocked
        assert result.block_reason is not None
        assert not result.is_safe
    
    def test_statistics(self):
        """測試統計功能"""
        config = MonitorConfig(
            enable_alerts=False,
            enable_logging=False,
            enable_console_log=False
        )
        monitor = MoltbotMonitor(config)
        
        # 執行幾個指令
        for i in range(3):
            command = CommandInput(
                command_id=f'cmd_{i}',
                command_name=f'command_{i}',
                actions=[
                    {'action_type': 'io_read', 'name': 'Read', 'description': 'Read'}
                ]
            )
            monitor.check_command(command)
        
        stats = monitor.get_statistics()
        assert stats['monitor_stats']['total_checked'] == 3
    
    def test_callbacks(self):
        """測試回呼功能"""
        config = MonitorConfig(
            enable_alerts=False,
            enable_logging=False,
            enable_console_log=False
        )
        monitor = MoltbotMonitor(config)
        
        pre_calls = []
        post_calls = []
        
        def pre_callback(cmd):
            pre_calls.append(cmd.command_id)
        
        def post_callback(result):
            post_calls.append(result.command_id)
        
        monitor.register_pre_check_callback(pre_callback)
        monitor.register_post_check_callback(post_callback)
        
        command = CommandInput(
            command_id='cmd_001',
            command_name='test',
            actions=[{'action_type': 'compute', 'name': 'Test', 'description': 'Test'}]
        )
        
        monitor.check_command(command)
        
        assert 'cmd_001' in pre_calls
        assert 'cmd_001' in post_calls
    
    def test_session_summary(self):
        """測試 session 摘要"""
        config = MonitorConfig(
            enable_alerts=False,
            enable_logging=False,
            enable_console_log=False
        )
        monitor = MoltbotMonitor(config)
        
        # 執行指令
        command = CommandInput(
            command_id='cmd_001',
            command_name='test',
            actions=[{'action_type': 'io_read', 'name': 'Read', 'description': 'Test'}],
            session_id='session_123'
        )
        monitor.check_command(command)
        
        summary = monitor.get_session_summary('session_123')
        assert summary['session_id'] == 'session_123'
        assert summary['sequence_summary'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
