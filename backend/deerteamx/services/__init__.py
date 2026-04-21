"""Business Logic Services Package

提供DeerTeamX核心业务逻辑服务层，包括：
- 团队管理服务 (team_service)
- 执行引擎服务 (execution_service) - TODO
- 模板管理服务 (template_service) - TODO
- CrewAI导入服务 (import_service) - TODO
"""

from deerteamx.services.team_service import TeamService

__all__ = ["TeamService"]
