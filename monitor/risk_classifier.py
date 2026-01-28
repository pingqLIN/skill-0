"""
風險分類器 (Risk Classifier)
基於 Skill-0 三元分類法的指令風險評估

將指令依據其 Action Type 和潛在影響分為不同風險等級
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime


class RiskLevel(Enum):
    """風險等級定義"""
    CRITICAL = auto()   # 立即危害 - 需即時警報
    HIGH = auto()       # 高風險 - 需警報 + 紀錄
    MEDIUM = auto()     # 中風險 - 需紀錄
    LOW = auto()        # 低風險 - 選擇性紀錄
    SAFE = auto()       # 安全 - 無需處理


@dataclass
class RiskProfile:
    """指令風險特徵"""
    level: RiskLevel
    category: str
    description: str
    action_type: str
    affected_resources: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    reversible: bool = True
    side_effects: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """風險評估結果"""
    command_id: str
    command_name: str
    profile: RiskProfile
    base_score: float          # 基礎風險分數 (0-100)
    context_score: float       # 上下文調整分數
    final_score: float         # 最終風險分數
    timestamp: datetime = field(default_factory=datetime.now)
    factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class RiskClassifier:
    """
    風險分類器
    
    基於 Skill-0 的 action_type 分類，評估指令風險等級
    """
    
    # 動作類型到風險等級的基礎映射 (參考 skill-decomposition.schema.json)
    ACTION_TYPE_RISKS: Dict[str, RiskProfile] = {
        # IO 操作
        'io_read': RiskProfile(
            level=RiskLevel.LOW,
            category='io',
            description='讀取操作，通常無副作用',
            action_type='io_read',
            reversible=True
        ),
        'io_write': RiskProfile(
            level=RiskLevel.MEDIUM,
            category='io',
            description='寫入操作，可能修改資料',
            action_type='io_write',
            affected_resources=['filesystem', 'database'],
            reversible=False,
            side_effects=['data_modification']
        ),
        
        # 外部呼叫
        'external_call': RiskProfile(
            level=RiskLevel.HIGH,
            category='network',
            description='外部 API 呼叫，可能洩漏資訊或觸發外部行為',
            action_type='external_call',
            affected_resources=['network', 'external_service'],
            requires_confirmation=True,
            reversible=False,
            side_effects=['network_request', 'data_transmission']
        ),
        
        # 狀態改變
        'state_change': RiskProfile(
            level=RiskLevel.MEDIUM,
            category='state',
            description='系統狀態改變',
            action_type='state_change',
            affected_resources=['system_state', 'configuration'],
            reversible=False,
            side_effects=['state_modification']
        ),
        
        # 計算
        'compute': RiskProfile(
            level=RiskLevel.LOW,
            category='processing',
            description='純計算操作，無副作用',
            action_type='compute',
            reversible=True
        ),
        
        # 資料轉換
        'transform': RiskProfile(
            level=RiskLevel.LOW,
            category='processing',
            description='資料轉換，通常無副作用',
            action_type='transform',
            reversible=True
        ),
        
        # LLM 推論
        'llm_inference': RiskProfile(
            level=RiskLevel.MEDIUM,
            category='ai',
            description='LLM 推論呼叫，可能消耗資源或產生不可預期輸出',
            action_type='llm_inference',
            affected_resources=['api_quota', 'compute_resources'],
            side_effects=['resource_consumption']
        ),
        
        # 等待輸入
        'await_input': RiskProfile(
            level=RiskLevel.LOW,
            category='interaction',
            description='等待使用者輸入',
            action_type='await_input',
            reversible=True
        ),
    }
    
    # 高風險關鍵字 (用於內容分析)
    HIGH_RISK_KEYWORDS: Set[str] = {
        'delete', 'remove', 'drop', 'truncate',      # 刪除操作
        'execute', 'exec', 'eval', 'run',            # 執行操作
        'admin', 'root', 'sudo', 'privilege',        # 權限相關
        'password', 'secret', 'credential', 'token', # 敏感資訊
        'transfer', 'send', 'transmit',              # 傳輸操作
        'modify', 'update', 'alter', 'change',       # 修改操作
        'install', 'deploy', 'publish',              # 部署操作
        'shutdown', 'restart', 'terminate',          # 系統控制
    }
    
    CRITICAL_KEYWORDS: Set[str] = {
        'format', 'wipe', 'destroy', 'purge',        # 破壞性操作
        'rm -rf', 'drop database', 'delete all',     # 危險命令
        'disable_security', 'bypass', 'override',    # 安全繞過
    }
    
    def __init__(self, custom_profiles: Optional[Dict[str, RiskProfile]] = None):
        """
        初始化風險分類器
        
        Args:
            custom_profiles: 自訂風險特徵映射
        """
        self.profiles = self.ACTION_TYPE_RISKS.copy()
        if custom_profiles:
            self.profiles.update(custom_profiles)
        
        self.keyword_weights = {
            'critical': 50,
            'high': 20,
            'medium': 10,
        }
    
    def classify_action(self, action: Dict[str, Any]) -> RiskProfile:
        """
        分類單一動作的風險
        
        Args:
            action: Skill-0 格式的 action 物件
            
        Returns:
            RiskProfile: 風險特徵
        """
        action_type = action.get('action_type', 'unknown')
        
        # 取得基礎風險特徵
        if action_type in self.profiles:
            profile = self.profiles[action_type]
        else:
            # 未知類型預設為中風險
            profile = RiskProfile(
                level=RiskLevel.MEDIUM,
                category='unknown',
                description=f'未知動作類型: {action_type}',
                action_type=action_type
            )
        
        # 根據動作描述調整風險等級
        description = action.get('description', '').lower()
        name = action.get('name', '').lower()
        content = f"{name} {description}"
        
        # 檢查關鍵字
        adjusted_profile = self._adjust_by_keywords(profile, content)
        
        # 檢查 side_effects
        if action.get('side_effects'):
            adjusted_profile = self._adjust_by_side_effects(
                adjusted_profile, 
                action['side_effects']
            )
        
        return adjusted_profile
    
    def _adjust_by_keywords(self, profile: RiskProfile, content: str) -> RiskProfile:
        """根據關鍵字調整風險等級"""
        content_lower = content.lower()
        
        # 檢查致命關鍵字
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword in content_lower:
                return RiskProfile(
                    level=RiskLevel.CRITICAL,
                    category=profile.category,
                    description=f'{profile.description} [偵測到危險關鍵字: {keyword}]',
                    action_type=profile.action_type,
                    affected_resources=profile.affected_resources,
                    requires_confirmation=True,
                    reversible=False,
                    side_effects=profile.side_effects + [f'critical_keyword:{keyword}']
                )
        
        # 檢查高風險關鍵字
        found_keywords = [kw for kw in self.HIGH_RISK_KEYWORDS if kw in content_lower]
        if found_keywords and profile.level.value > RiskLevel.HIGH.value:
            return RiskProfile(
                level=RiskLevel.HIGH,
                category=profile.category,
                description=f'{profile.description} [偵測到風險關鍵字: {", ".join(found_keywords)}]',
                action_type=profile.action_type,
                affected_resources=profile.affected_resources,
                requires_confirmation=True,
                reversible=profile.reversible,
                side_effects=profile.side_effects + [f'high_risk_keyword:{kw}' for kw in found_keywords]
            )
        
        return profile
    
    def _adjust_by_side_effects(
        self, 
        profile: RiskProfile, 
        side_effects: List[str]
    ) -> RiskProfile:
        """根據副作用調整風險等級"""
        critical_effects = {'data_loss', 'system_crash', 'security_breach'}
        high_effects = {'data_modification', 'state_change', 'external_communication'}
        
        effect_set = set(se.lower() for se in side_effects)
        
        if effect_set & critical_effects:
            return RiskProfile(
                level=RiskLevel.CRITICAL,
                category=profile.category,
                description=f'{profile.description} [危險副作用]',
                action_type=profile.action_type,
                affected_resources=profile.affected_resources,
                requires_confirmation=True,
                reversible=False,
                side_effects=profile.side_effects + side_effects
            )
        
        if effect_set & high_effects and profile.level.value > RiskLevel.HIGH.value:
            return RiskProfile(
                level=RiskLevel.HIGH,
                category=profile.category,
                description=f'{profile.description} [高風險副作用]',
                action_type=profile.action_type,
                affected_resources=profile.affected_resources,
                requires_confirmation=True,
                reversible=profile.reversible,
                side_effects=profile.side_effects + side_effects
            )
        
        return profile
    
    def assess_command(
        self, 
        command_id: str,
        command_name: str,
        actions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        評估完整指令的風險
        
        Args:
            command_id: 指令識別碼
            command_name: 指令名稱
            actions: 指令包含的動作列表
            context: 執行上下文 (可選)
            
        Returns:
            RiskAssessment: 風險評估結果
        """
        if not actions:
            return RiskAssessment(
                command_id=command_id,
                command_name=command_name,
                profile=RiskProfile(
                    level=RiskLevel.LOW,
                    category='empty',
                    description='空指令',
                    action_type='none'
                ),
                base_score=0.0,
                context_score=0.0,
                final_score=0.0,
                factors=['no_actions']
            )
        
        # 評估每個動作
        profiles = [self.classify_action(action) for action in actions]
        
        # 取最高風險等級
        highest_risk = min(profiles, key=lambda p: p.level.value)
        
        # 計算基礎分數
        base_score = self._calculate_base_score(profiles)
        
        # 計算上下文分數
        context_score = self._calculate_context_score(context) if context else 0.0
        
        # 最終分數
        final_score = min(100.0, base_score + context_score)
        
        # 收集因素
        factors = self._collect_factors(profiles)
        
        # 生成建議
        recommendations = self._generate_recommendations(highest_risk, final_score)
        
        return RiskAssessment(
            command_id=command_id,
            command_name=command_name,
            profile=highest_risk,
            base_score=base_score,
            context_score=context_score,
            final_score=final_score,
            factors=factors,
            recommendations=recommendations
        )
    
    def _calculate_base_score(self, profiles: List[RiskProfile]) -> float:
        """計算基礎風險分數"""
        level_scores = {
            RiskLevel.CRITICAL: 90,
            RiskLevel.HIGH: 70,
            RiskLevel.MEDIUM: 40,
            RiskLevel.LOW: 15,
            RiskLevel.SAFE: 0,
        }
        
        if not profiles:
            return 0.0
        
        # 使用最高分數 + 累加因子
        scores = [level_scores.get(p.level, 50) for p in profiles]
        max_score = max(scores)
        
        # 多個高風險動作會略微增加總分
        high_risk_count = sum(1 for p in profiles if p.level.value <= RiskLevel.HIGH.value)
        additional = min(10, high_risk_count * 2)
        
        return min(100.0, max_score + additional)
    
    def _calculate_context_score(self, context: Dict[str, Any]) -> float:
        """計算上下文風險分數"""
        score = 0.0
        
        # 檢查是否有敏感資源
        if context.get('sensitive_resources'):
            score += 15
        
        # 檢查是否在生產環境
        if context.get('environment') == 'production':
            score += 20
        
        # 檢查執行者權限
        if context.get('privilege_level') == 'admin':
            score += 10
        
        # 檢查是否有外部連線
        if context.get('external_connection'):
            score += 10
        
        return score
    
    def _collect_factors(self, profiles: List[RiskProfile]) -> List[str]:
        """收集風險因素"""
        factors = []
        
        for p in profiles:
            if p.level == RiskLevel.CRITICAL:
                factors.append(f'CRITICAL: {p.description}')
            elif p.level == RiskLevel.HIGH:
                factors.append(f'HIGH: {p.description}')
            
            for effect in p.side_effects:
                factors.append(f'side_effect: {effect}')
            
            if not p.reversible:
                factors.append(f'irreversible: {p.action_type}')
        
        return list(set(factors))  # 去重
    
    def _generate_recommendations(
        self, 
        profile: RiskProfile, 
        score: float
    ) -> List[str]:
        """生成安全建議"""
        recommendations = []
        
        if score >= 90:
            recommendations.append('⛔ 此操作極度危險，建議禁止執行')
            recommendations.append('🔍 請確認操作必要性與授權')
        elif score >= 70:
            recommendations.append('⚠️ 此操作風險較高，需要人工審核')
            recommendations.append('📝 確保已備份相關資料')
        elif score >= 40:
            recommendations.append('⚡ 此操作有一定風險，建議記錄操作日誌')
        
        if not profile.reversible:
            recommendations.append('🔄 此操作不可逆，請謹慎執行')
        
        if profile.requires_confirmation:
            recommendations.append('✋ 需要使用者確認後才能執行')
        
        return recommendations
