"""DeerTeamX 模板管理器。

该模块负责管理团队配置模板，支持从现有团队创建模板、
基于模板快速实例化新团队，以及模板的分类检索。
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from deerteamx.models.base import Template, Team

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
        scope: str = "personal",
        user_id: str = "system"
    ) -> Template:
        """从现有的团队配置创建一个模板。"""
        # 1. 获取团队当前配置
        stmt = select(Team).where(Team.team_id == team_id)
        result = await self.db.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            raise ValueError(f"Team {team_id} not found")

        # 2. 生成模板ID
        import uuid
        template_id = f"tpl-{uuid.uuid4().hex[:12]}"

        # 3. 创建模板记录
        template = Template(
            template_id=template_id,
            template_name=template_name,
            description=description,
            scope=scope,
            config_snapshot=team.config_snapshot,
            creator_id=user_id,
            usage_count=0
        )
        
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        
        logger.info(f"Created template '{template_name}' from team {team_id}")
        return template

    async def list_templates(self, scope: Optional[str] = None) -> List[Template]:
        """获取模板列表，支持按范围筛选。"""
        stmt = select(Template).order_by(desc(Template.created_at))
        if scope:
            stmt = stmt.where(Template.scope == scope)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def instantiate_team_from_template(
        self, 
        template_id: str, 
        new_team_name: str,
        user_id: str
    ) -> Dict[str, Any]:
        """基于模板实例化一个新的团队。"""
        stmt = select(Template).where(Template.template_id == template_id)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # 返回模板配置供调用方创建团队
        return {
            "name": new_team_name,
            "config": template.config_snapshot,
            "source_template": template.template_name
        }

