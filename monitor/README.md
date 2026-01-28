# Moltbot Monitor Extension

> 基於 Skill-0 篩選器技術的即時監督程序

## 概述

Moltbot Monitor 是一個輕量化的擴充協作程式，利用 Skill-0 的三元分類系統（Action / Rule / Directive）來即時監督 Moltbot 執行程序的動作。

### 主要功能

1. **指令風險評估 (Risk Classification)** - 根據動作類型評估單一指令的風險等級
2. **序列分析 (Sequence Analysis)** - 分析連續指令的搭配模式，偵測危險組合
3. **即時警報 (Real-time Alerts)** - 對立即性危害提供即時通知
4. **風險日誌 (Risk Logging)** - 記錄所有風險操作供後續審計

## 架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                     Moltbot Monitor                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │    指令輸入    │──▶│  風險分類器   │──▶│     序列分析器        │   │
│  │   Command     │  │ RiskClassifier│  │  SequenceAnalyzer    │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                           │                      │               │
│                           ▼                      ▼               │
│                    ┌──────────────────────────────────┐          │
│                    │         監督結果評估              │          │
│                    │    MonitorResult Evaluation      │          │
│                    └──────────────────────────────────┘          │
│                           │                      │               │
│              ┌────────────┴────────────┐         │               │
│              ▼                         ▼         ▼               │
│  ┌──────────────────┐      ┌──────────────────────────┐         │
│  │    警報管理器     │      │       風險日誌            │         │
│  │   AlertManager   │      │      RiskLogger          │         │
│  └──────────────────┘      └──────────────────────────┘         │
│         │                              │                         │
│         ▼                              ▼                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │  即時通知   │  │  日誌檔案   │  │  JSON 紀錄  │                 │
│  │ Real-time  │  │ Log Files  │  │  JSONL     │                 │
│  └────────────┘  └────────────┘  └────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 安裝

```bash
# 確保已安裝 Skill-0 的相依套件
pip install -r requirements.txt
```

## 快速開始

### 基本使用

```python
from monitor import MoltbotMonitor, MonitorConfig, CommandInput, RiskLevel

# 建立監督器
config = MonitorConfig(
    alert_threshold_level=RiskLevel.HIGH,
    enable_console_log=True
)
monitor = MoltbotMonitor(config)

# 定義要執行的指令
command = CommandInput(
    command_id='cmd_001',
    command_name='read_file',
    actions=[
        {
            'action_type': 'io_read',
            'name': 'Read File',
            'description': 'Read configuration file'
        }
    ],
    session_id='session_123',
    user_id='user_456'
)

# 檢查指令
result = monitor.check_command(command)

# 根據結果決定是否執行
if result.is_safe:
    print("✓ 指令安全，可以執行")
else:
    print(f"✗ 指令被阻擋: {result.block_reason}")
    for rec in result.recommendations:
        print(f"  建議: {rec}")
```

### 監督危險操作

```python
# 危險操作範例
dangerous_command = CommandInput(
    command_id='cmd_002',
    command_name='delete_database',
    actions=[
        {
            'action_type': 'io_write',
            'name': 'Delete',
            'description': 'Drop all database tables',
            'side_effects': ['data_loss']
        }
    ],
    session_id='session_123'
)

result = monitor.check_command(dangerous_command)
print(f"風險等級: {result.risk_assessment.profile.level.name}")
print(f"風險分數: {result.risk_assessment.final_score}")
print(f"被阻擋: {result.blocked}")
```

### 使用便捷函數

```python
from monitor import create_monitor, CommandInput

# 快速建立監督器
monitor = create_monitor(
    alert_threshold=RiskLevel.MEDIUM,
    enable_console=True,
    log_dir='./logs'
)

# 使用監督器...
```

## 風險等級

| 等級 | 說明 | 處理方式 |
|------|------|----------|
| **CRITICAL** | 立即危害 | 阻擋 + 即時警報 + 日誌 |
| **HIGH** | 高風險 | 警報 + 日誌 |
| **MEDIUM** | 中風險 | 日誌記錄 |
| **LOW** | 低風險 | 選擇性記錄 |
| **SAFE** | 安全 | 無需處理 |

## 動作類型風險映射

基於 Skill-0 schema 的 `action_type`：

| Action Type | 預設風險 | 說明 |
|-------------|----------|------|
| `io_read` | LOW | 讀取操作，通常無副作用 |
| `io_write` | MEDIUM | 寫入操作，可能修改資料 |
| `external_call` | HIGH | 外部 API 呼叫 |
| `state_change` | MEDIUM | 系統狀態改變 |
| `compute` | LOW | 純計算操作 |
| `transform` | LOW | 資料轉換 |
| `llm_inference` | MEDIUM | LLM 推論呼叫 |
| `await_input` | LOW | 等待使用者輸入 |

## 序列分析

### 危險序列模式

監督器會偵測以下危險的指令組合模式：

| 模式 | 說明 | 觸發序列 |
|------|------|----------|
| `ESCALATION` | 權限升級嘗試 | io_read → state_change |
| `DATA_EXFILTRATION` | 資料外洩 | io_read → external_call |
| `DESTRUCTIVE_CHAIN` | 破壞性指令鏈 | io_write → io_write |
| `BYPASS_ATTEMPT` | 安全繞過嘗試 | state_change → external_call |
| `RECONNAISSANCE` | 偵察行為 | io_read → io_read → io_read |
| `PERSISTENCE` | 持久化攻擊 | io_write → state_change |

### 序列分析配置

```python
config = MonitorConfig(
    enable_sequence_analysis=True,
    sequence_window_size=10,        # 追蹤最近 10 個指令
    sequence_time_window_minutes=5  # 5 分鐘時間窗口
)
```

## 自訂警報處理器

```python
from monitor import MoltbotMonitor, Alert, AlertType

def my_alert_handler(alert: Alert):
    """自訂警報處理器"""
    if alert.alert_type == AlertType.IMMEDIATE:
        # 發送緊急通知
        send_urgent_notification(alert)
    else:
        # 記錄到監控系統
        log_to_monitoring_system(alert)

monitor = MoltbotMonitor()
monitor.register_alert_handler(
    my_alert_handler,
    alert_types=[AlertType.IMMEDIATE, AlertType.PRIORITY]
)
```

## 日誌查詢

```python
# 查詢特定 session 的日誌
logs = monitor.risk_logger.query_logs(
    session_id='session_123',
    risk_level=RiskLevel.HIGH,
    limit=100
)

for entry in logs:
    print(f"{entry.timestamp}: {entry.message}")

# 取得統計
stats = monitor.risk_logger.get_statistics()
print(f"高風險事件: {stats['high_risk_count']}")

# 匯出日誌
monitor.risk_logger.export_logs(
    './export/risk_logs.json',
    format='json'
)
```

## 進階配置

### 完整配置範例

```python
from monitor import MonitorConfig, RiskLevel

config = MonitorConfig(
    # 風險分類設定
    enable_risk_classification=True,
    custom_risk_profiles=None,  # 可自訂風險映射
    
    # 序列分析設定
    enable_sequence_analysis=True,
    sequence_window_size=10,
    sequence_time_window_minutes=5,
    
    # 警報設定
    enable_alerts=True,
    alert_threshold_level=RiskLevel.HIGH,
    enable_async_alerts=True,
    
    # 日誌設定
    enable_logging=True,
    log_directory='./logs',
    min_log_level=RiskLevel.LOW,
    enable_console_log=True,
    enable_file_log=True,
    enable_json_log=True
)

monitor = MoltbotMonitor(config)
```

### 自訂風險特徵

```python
from monitor import RiskClassifier, RiskProfile, RiskLevel

custom_profiles = {
    'custom_action': RiskProfile(
        level=RiskLevel.HIGH,
        category='custom',
        description='自訂高風險操作',
        action_type='custom_action',
        affected_resources=['custom_resource'],
        requires_confirmation=True,
        reversible=False,
        side_effects=['custom_effect']
    )
}

classifier = RiskClassifier(custom_profiles=custom_profiles)
```

## API 整合

監督器可以輕鬆整合到現有的 API 中：

```python
from fastapi import FastAPI, HTTPException
from monitor import MoltbotMonitor, CommandInput

app = FastAPI()
monitor = MoltbotMonitor()

@app.post("/execute")
async def execute_command(command_data: dict):
    # 建立 CommandInput
    command = CommandInput(
        command_id=command_data['id'],
        command_name=command_data['name'],
        actions=command_data['actions'],
        session_id=command_data.get('session_id')
    )
    
    # 監督檢查
    result = monitor.check_command(command)
    
    if not result.is_safe:
        raise HTTPException(
            status_code=403,
            detail={
                'blocked': True,
                'reason': result.block_reason,
                'recommendations': result.recommendations
            }
        )
    
    # 執行指令...
    return {"status": "executed", "command_id": command.command_id}
```

## 效能考量

- 風險評估延遲: < 5ms
- 序列分析延遲: < 10ms
- 記憶體使用: ~50MB (包含序列歷史)
- 非同步警報處理，不阻擋主流程

## 版本

- Version: 1.0.0
- 基於 Skill-0 Schema v2.0.0
- 作者: pingqLIN

## 授權

MIT License
