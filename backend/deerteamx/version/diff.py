"""DeerTeamX 配置差异计算引擎。

该模块利用 jsondiffpatch 算法计算两个团队配置版本之间的差异，
并提供格式化的输出以便前端展示。
"""

import logging
from typing import Dict, Any, List

try:
    from jsondiff import diff
except ImportError:
    # 如果未安装 jsondiff，使用简单的字典对比作为兜底
    def diff(a: dict, b: dict) -> dict:
        """Simple diff fallback."""
        return {k: b[k] for k in b if k not in a or a[k] != b[k]}

logger = logging.getLogger(__name__)


class DiffEngine:
    """配置差异计算核心类。"""

    @staticmethod
    def calculate_diff(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """计算两个配置字典之间的差异。
        
        Args:
            old_config: 旧版本的配置。
            new_config: 新版本的配置。
            
        Returns:
            包含差异内容的字典。
        """
        try:
            # jsondiff 返回的 delta 格式：
            # - 新增字段: {"key": "new_value"}
            # - 删除字段: {"key": delete} (特殊标记)
            # - 修改字段: {"key": "modified_value"}
            return diff(old_config, new_config, marshal=True)
        except Exception as e:
            logger.error(f"Failed to calculate diff: {e}")
            return {}

    @staticmethod
    def format_diff_for_ui(diff_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """将差异结果格式化为前端友好的列表形式。
        
        Returns:
            例如: [{"path": "roles[0].model", "action": "modified", "old": "...", "new": "..."}]
        """
        changes = []
        DiffEngine._traverse_diff(diff_result, "", changes)
        return changes

    @classmethod
    def _traverse_diff(cls, data: Any, path: str, changes: List[Dict[str, str]]):
        """递归遍历差异树并生成扁平化列表。"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, dict):
                    cls._traverse_diff(value, new_path, changes)
                else:
                    # 简化处理：实际项目中需区分 insert/delete/replace
                    changes.append({
                        "path": new_path,
                        "action": "modified",
                        "value": str(value)
                    })
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                if isinstance(item, dict):
                    cls._traverse_diff(item, new_path, changes)
                else:
                    changes.append({
                        "path": new_path,
                        "action": "modified",
                        "value": str(item)
                    })
