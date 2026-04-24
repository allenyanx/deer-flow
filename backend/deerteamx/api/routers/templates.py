"""DeerTeamX 模板管理 API 路由。

该模块提供团队配置模板的保存、检索及实例化功能。
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.database.session import get_db
from deerteamx.template.manager import TemplateManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/templates",
    tags=["template-management"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
    },
)


@router.get("", response_model=List[dict])
async def list_templates(
    scope: Optional[str] = Query(None, pattern="^(system|personal|all)$"),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """列出可用模板（系统 + 个人）。"""
    manager = TemplateManager(db)
    # 简化实现：目前返回所有模板，后续可根据 scope 和 keyword 过滤
    templates = await manager.list_templates(scope if scope != "all" else None)
    return [
        {
            "template_id": t.template_id,
            "name": t.template_name,
            "scope": t.scope,
            "usage_count": t.usage_count
        } 
        for t in templates
    ]


@router.post("/{template_id}/use", response_model=dict, status_code=status.HTTP_201_CREATED)
async def use_template(
    template_id: str, 
    team_name: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = "test-user"
) -> Any:
    """基于模板创建新团队。"""
    try:
        manager = TemplateManager(db)
        result = await manager.instantiate_team_from_template(template_id, team_name, user_id)
        return {
            "message": f"Team '{team_name}' created from template",
            "config": result["config"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
