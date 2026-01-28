#!/usr/bin/env python3
"""
Moltbot Monitor 示範腳本
展示監督程序的主要功能
"""

import sys
from pathlib import Path

# 確保可以 import monitor 模組
sys.path.insert(0, str(Path(__file__).parent))

from monitor import (
    MoltbotMonitor, 
    MonitorConfig, 
    CommandInput,
    RiskLevel,
    create_monitor
)


def demo_basic_usage():
    """基本使用示範"""
    print("\n" + "="*60)
    print("📋 基本使用示範")
    print("="*60)
    
    # 建立監督器
    config = MonitorConfig(
        enable_alerts=False,
        enable_logging=False,
        enable_console_log=False
    )
    monitor = MoltbotMonitor(config)
    
    # 安全指令
    safe_command = CommandInput(
        command_id='cmd_001',
        command_name='read_config',
        actions=[
            {
                'action_type': 'io_read',
                'name': 'Read Config',
                'description': 'Read application configuration file'
            }
        ],
        session_id='demo_session'
    )
    
    result = monitor.check_command(safe_command)
    
    print(f"\n指令: {safe_command.command_name}")
    print(f"  風險等級: {result.risk_assessment.profile.level.name}")
    print(f"  風險分數: {result.risk_assessment.final_score:.1f}")
    print(f"  是否安全: {'✓ 安全' if result.is_safe else '✗ 不安全'}")
    print(f"  是否阻擋: {'是' if result.blocked else '否'}")


def demo_dangerous_command():
    """危險指令示範"""
    print("\n" + "="*60)
    print("⚠️ 危險指令示範")
    print("="*60)
    
    monitor = create_monitor(enable_console=False)
    
    # 危險指令 - 刪除操作
    dangerous_command = CommandInput(
        command_id='cmd_002',
        command_name='wipe_database',
        actions=[
            {
                'action_type': 'io_write',
                'name': 'Wipe Database',
                'description': 'Wipe all database records permanently',
                'side_effects': ['data_loss']
            }
        ],
        session_id='demo_session'
    )
    
    result = monitor.check_command(dangerous_command)
    
    print(f"\n指令: {dangerous_command.command_name}")
    print(f"  風險等級: {result.risk_assessment.profile.level.name}")
    print(f"  風險分數: {result.risk_assessment.final_score:.1f}")
    print(f"  是否安全: {'✓ 安全' if result.is_safe else '✗ 不安全'}")
    print(f"  是否阻擋: {'是' if result.blocked else '否'}")
    
    if result.blocked:
        print(f"  阻擋原因: {result.block_reason}")
    
    if result.recommendations:
        print(f"  建議:")
        for rec in result.recommendations:
            print(f"    - {rec}")
    
    monitor.shutdown()


def demo_sequence_analysis():
    """序列分析示範"""
    print("\n" + "="*60)
    print("🔗 序列分析示範 (資料外洩模式)")
    print("="*60)
    
    config = MonitorConfig(
        enable_alerts=False,
        enable_logging=False,
        enable_console_log=False,
        enable_sequence_analysis=True
    )
    monitor = MoltbotMonitor(config)
    
    # 模擬可疑序列: 讀取敏感資料 -> 外部呼叫
    commands = [
        CommandInput(
            command_id='seq_001',
            command_name='read_user_data',
            actions=[
                {'action_type': 'io_read', 'name': 'Read', 'description': 'Read user sensitive data'}
            ],
            session_id='sequence_demo'
        ),
        CommandInput(
            command_id='seq_002',
            command_name='send_to_external',
            actions=[
                {'action_type': 'external_call', 'name': 'Send', 'description': 'Send data to external server'}
            ],
            session_id='sequence_demo'
        )
    ]
    
    print("\n執行指令序列:")
    for i, cmd in enumerate(commands, 1):
        result = monitor.check_command(cmd)
        print(f"\n{i}. {cmd.command_name}")
        print(f"   風險等級: {result.risk_assessment.profile.level.name}")
        
        if result.sequence_alerts:
            print(f"   ⚠️ 序列警報:")
            for alert in result.sequence_alerts:
                print(f"      - {alert.pattern.name}: {alert.description}")
                print(f"        信心度: {alert.confidence:.2%}")
    
    # 顯示 session 摘要
    summary = monitor.get_session_summary('sequence_demo')
    print(f"\nSession 摘要:")
    print(f"  指令數量: {summary['sequence_summary']['command_count']}")
    
    monitor.shutdown()


def demo_risk_levels():
    """各種風險等級示範"""
    print("\n" + "="*60)
    print("📊 風險等級示範")
    print("="*60)
    
    monitor = create_monitor(enable_console=False)
    
    test_cases = [
        ('transform_data', 'transform', '資料轉換', []),
        ('compute_stats', 'compute', '計算統計', []),
        ('read_file', 'io_read', '讀取檔案', []),
        ('write_log', 'io_write', '寫入日誌', []),
        ('call_api', 'external_call', 'API 呼叫', []),
        ('change_config', 'state_change', '修改設定', []),
        ('delete_records', 'io_write', '刪除記錄', ['data_modification']),
        ('format_disk', 'io_write', '格式化磁碟 (format disk)', ['data_loss']),
    ]
    
    print(f"\n{'指令名稱':<20} {'動作類型':<15} {'風險等級':<10} {'分數':>6}")
    print("-"*55)
    
    for name, action_type, desc, side_effects in test_cases:
        cmd = CommandInput(
            command_id=f'risk_{name}',
            command_name=name,
            actions=[{
                'action_type': action_type,
                'name': name,
                'description': desc,
                'side_effects': side_effects
            }]
        )
        
        result = monitor.check_command(cmd)
        level = result.risk_assessment.profile.level.name
        score = result.risk_assessment.final_score
        
        # 添加顏色標記
        if level == 'CRITICAL':
            marker = '🔴'
        elif level == 'HIGH':
            marker = '🟠'
        elif level == 'MEDIUM':
            marker = '🟡'
        else:
            marker = '🟢'
        
        print(f"{name:<20} {action_type:<15} {marker} {level:<8} {score:>6.1f}")
    
    monitor.shutdown()


def demo_statistics():
    """統計資訊示範"""
    print("\n" + "="*60)
    print("📈 統計資訊示範")
    print("="*60)
    
    monitor = create_monitor(enable_console=False)
    
    # 模擬多個指令
    for i in range(10):
        cmd = CommandInput(
            command_id=f'stat_{i}',
            command_name=f'command_{i}',
            actions=[{
                'action_type': ['io_read', 'io_write', 'compute', 'external_call'][i % 4],
                'name': f'Action {i}',
                'description': f'Test action {i}'
            }],
            session_id='stats_demo'
        )
        monitor.check_command(cmd)
    
    stats = monitor.get_statistics()
    
    print(f"\n監督統計:")
    print(f"  檢查總數: {stats['monitor_stats']['total_checked']}")
    print(f"  阻擋數量: {stats['monitor_stats']['blocked']}")
    print(f"\n風險等級分布:")
    for level, count in stats['monitor_stats']['by_risk_level'].items():
        if count > 0:
            print(f"  {level}: {count}")
    
    monitor.shutdown()


def main():
    """主程式"""
    print("\n" + "="*60)
    print("🔍 Moltbot Monitor Extension - 功能示範")
    print("   基於 Skill-0 篩選器技術的即時監督程序")
    print("="*60)
    
    demo_basic_usage()
    demo_dangerous_command()
    demo_sequence_analysis()
    demo_risk_levels()
    demo_statistics()
    
    print("\n" + "="*60)
    print("✅ 示範完成!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
