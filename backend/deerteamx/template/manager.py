"""DeerTeamX 模板管理器。

该模块负责管理团队配置模板，支持从现有团队创建模板、
基于模板快速实例化新团队，以及模板的分类检索。
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from deerteamx.models.template import TeamTemplate
from deerteamx.models.team import Team

logger = logging.getLogger(__name__)


class TemplateManager:
    """团队配置模板管理核心类。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_template_from_team(
        self, 
        team_id: str, 
        template_name: str, 
        description: str,
        category: str = "general",
        user_id: str = "system"
    ) -> TeamTemplate:
        """从现有的团队配置创建一个模板。"""
        # 1. 获取团队当前配置
        stmt = select(Team).where(Team.team_id == team_id)
        result = await self.db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            raise ValueError(f"Team {team_id} not found")

        # 2. 创建模板记录
        template = TeamTemplate(
            name=template_name,
            description=description,
            category=category,
            config_snapshot=team.config_data, # 假设 Team 模型中有 config_data 字段
            created_by=user_id
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        logger.info(f"Created template '{template_name}' from team {team_id}")
        return template

    async def list_templates(self, category: Optional[str] = None) -> List[TeamTemplate]:
        """获取模板列表，支持按分类筛选。"""
        stmt = select(TeamTemplate).order_by(desc(TeamTemplate.created_at))
        if category:
            stmt = stmt.where(TeamTemplate.category == category)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def instantiate_team_from_template(
        self, 
        template_id: int, 
        new_team_name: str,
        user_id: str
    ) -> Dict[str, Any]:
        """基于模板实例化一个新的团队。"""
        stmt = select(TeamTemplate).where(TeamTemplate.id == template_id)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # 返回模板配置供调用方创建团队
        return {
            "name": new_team_name,
            "config": template.config_snapshot,
            "source_template": template.name
        }


class TeamTemplate(Base):
    """团队模板数据模型。"""
    __tablename__ = "team_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    category = Column(String(50), default="general")
    config_snapshot = Column(JSON, nullable=False)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_public = Column(Boolean, default=False)
