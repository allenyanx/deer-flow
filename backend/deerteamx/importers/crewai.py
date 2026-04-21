"""DeerTeamX CrewAI 配置导入器。

该模块负责将 CrewAI (v0.50+) 的 YAML/JSON 配置解析并映射为
DeerTeamX 的团队配置格式，同时处理 process_type 和共识参数。
"""

import json
import logging
import re
from typing import Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)


class CrewAIImporter:
    """CrewAI v0.50+ 配置导入器。"""

    # 核心字段清单 — 100% 兼容导入
    CORE_FIELDS = {
        "roles": ["name", "role", "goal", "backstory", "allow_delegation"],
        "tasks": ["description", "expected_output", "agent", "tools"],
        "crew": ["name", "process", "manager_llm"],
    }

    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def parse(self, file_content: str, format: str = "yaml") -> Tuple[dict, list, list]:
        """解析 CrewAI 配置并映射为 DeerTeamX Schema。"""
        try:
            data = yaml.safe_load(file_content) if format == "yaml" else json.loads(file_content)
        except Exception as e:
            return {}, [], [f"解析失败: {str(e)}"]

        self.warnings = []
        self.errors = []

        # 1. 验证核心字段
        self._validate_core_fields(data)
        if self.errors:
            return {}, [], self.errors

        # 2. 映射为 DeerTeamX Schema
        config = self._map_to_deerteamx_schema(data)

        return config, self.warnings, self.errors

    def _validate_core_fields(self, data: dict):
        """验证 CrewAI 配置中的核心字段是否存在。"""
        for section, fields in self.CORE_FIELDS.items():
            if section not in data:
                self.errors.append(f"缺少核心部分: {section}")
                continue
            if isinstance(data[section], list):
                for item in data[section]:
                    for field in fields:
                        if field not in item:
                            self.warnings.append(f"{section} 中缺少建议字段: {field}")

    def _map_to_deerteamx_schema(self, crewai_data: dict) -> dict:
        """将 CrewAI 格式映射为 DeerTeamX 团队配置格式。"""
        roles = []
        tasks = []

        # CrewAI roles → DeerTeamX roles
        for role in crewai_data.get("roles", []):
            roles.append({
                "role_id": self._slugify(role["name"]),
                "agent_name": self._slugify(role["name"]),
                "name": role["name"],
                "description": role.get("backstory", ""),
                "goal": role["goal"],
                "model": "gpt-4",  # 默认模型
                "tool_groups": [],
            })

        # CrewAI tasks → DeerTeamX tasks
        for task in crewai_data.get("tasks", []):
            tasks.append({
                "task_id": self._slugify(task["description"][:30]),
                "description": task["description"],
                "expected_output": task.get("expected_output", ""),
                "assigned_role": task.get("agent", ""),
                "dependencies": [],
            })

        # 处理 process_type 映射
        crew_process = crewai_data.get("crew", {}).get("process", "sequential")
        execution_mode = "static"
        consensus_params = None

        if crew_process == "hierarchical":
            execution_mode = "hierarchical"
        elif crew_process == "consensus":
            execution_mode = "consensus"
            # 补充共识参数的默认值
            consensus_params = {
                "threshold": crewai_data.get("crew", {}).get("consensus_threshold", 0.75),
                "max_iterations": crewai_data.get("crew", {}).get("max_consensus_iterations", 3)
            }

        return {
            "name": crewai_data.get("crew", {}).get("name", "Imported Team"),
            "execution_mode": execution_mode,
            "roles": roles,
            "tasks": tasks,
            "version": "0.1.0",
            "imported_from": "crewai",
            "consensus_params": consensus_params,
        }

    @staticmethod
    def _slugify(text: str) -> str:
        """将文本转换为合法的 ID 格式（小写、连字符）。"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        return text
