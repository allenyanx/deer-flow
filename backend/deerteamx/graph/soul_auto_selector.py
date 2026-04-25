"""SOUL.md 自动选择算法

基于角色特征（name/goal/backstory）的关键词启发式匹配，智能推荐最合适的模板。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def auto_select_template(role: Dict[str, Any]) -> str:
    """根据角色特征自动选择最合适的模板
    
    启发式规则：
    - 包含「分析」「研究」「审计」等关键词 → expert_analyst
    - 包含「创作」「撰写」「设计」等关键词 → creative_creator
    - 包含「开发」「编程」「工程」等关键词 → technical_developer
    - 包含「管理」「协调」「领导」等关键词 → coordinator_manager
    - 包含「测试」「审核」「质检」等关键词 → quality_assurance
    - 其他 → default
    
    Args:
        role: 角色配置字典
        
    Returns:
        推荐的模板名称
    """
    # 提取角色的文本特征（name + goal + backstory）
    text_features = " ".join([
        role.get("name", ""),
        role.get("goal", ""),
        role.get("backstory", ""),
    ]).lower()
    
    # 关键词映射表
    keyword_mapping = {
        "expert_analyst": [
            "分析", "analyze", "research", "研究", "audit", "审计",
            "investigate", "调查", "evaluate", "评估", "inspect", "检查"
        ],
        "creative_creator": [
            "创作", "create", "write", "撰写", "design", "设计",
            "content", "内容", "copy", "文案", "marketing", "营销"
        ],
        "technical_developer": [
            "开发", "develop", "code", "代码", "program", "编程",
            "engineer", "工程", "architect", "架构", "debug", "调试"
        ],
        "coordinator_manager": [
            "管理", "manage", "coordinate", "协调", "lead", "领导",
            "project", "项目", "organize", "组织", "facilitate", "促进"
        ],
        "quality_assurance": [
            "测试", "test", "qa", "quality", "质量", "review", "审查",
            "verify", "验证", "validate", "确认", "inspect", "检验"
        ],
    }
    
    # 计算每个模板的匹配得分
    scores = {}
    for template_name, keywords in keyword_mapping.items():
        score = sum(1 for keyword in keywords if keyword in text_features)
        scores[template_name] = score
    
    # 选择得分最高的模板
    best_template = max(scores, key=scores.get)
    best_score = scores[best_template]
    
    # 如果最高分为 0，使用默认模板
    if best_score == 0:
        return "default"
    
    logger.debug(
        f"Auto-selected template '{best_template}' for role "
        f"'{role.get('name')}' (score={best_score})"
    )
    
    return best_template
