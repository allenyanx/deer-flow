"""Team Management API Routes

提供团队管理的RESTful API接口，包括：
- 团队CRUD操作
- 名称唯一性校验
- 分页查询与筛选
- 权限控制与资源归属校验
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.api.schemas.team_schemas import (
    CreateTeamRequest,
    UpdateTeamRequest,
    TeamDetail,
    TeamListResponse,
    TeamSummary,
    NameAvailabilityResponse,
    PaginationInfo,
)
from deerteamx.database.session import get_db
from deerteamx.services.team_service import TeamService
from deerteamx.api.dependencies import get_current_user
from deerteamx.models.base import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/teams",
    tags=["team-management"],
    responses={
        401: {"description": "Unauthorized - 未认证或Token过期"},
        403: {"description": "Forbidden - 无权限访问此资源"},
        404: {"description": "Not Found - 团队不存在"},
        409: {"description": "Conflict - 名称冲突或版本冲突"},
        423: {"description": "Locked - 团队正在执行中"},
    },
)


@router.post("", response_model=TeamDetail, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: CreateTeamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """创建新团队配置。
    
    业务流程：
    1. 验证团队名称唯一性（同一用户下）
    2. 为每个角色创建DeerFlow Custom Agent
    3. 保存团队配置到数据库
    4. 创建初始版本快照（v0.1.0）
    
    Args:
        data: 团队配置数据（包含roles/tasks/global_settings）
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        创建的团队详情（含team_id和version）
        
    Raises:
        HTTPException: 409 如果团队名称已存在
        HTTPException: 422 如果参数校验失败
        
    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/teams \
          -H "Authorization: Bearer <token>" \
          -H "Content-Type: application/json" \
          -d '{
            "name": "代码审查团队",
            "execution_mode": "static",
            "roles": [...],
            "tasks": [...],
            "global_settings": {...}
          }'
        ```
    """
    try:
        # 调用服务层创建团队
        service = TeamService(db)
        team = await service.create_team(
            team_data=data.dict(),
            user_id=current_user.user_id
        )
        
        logger.info(f"✅ 团队创建成功: team_id={team.team_id}, user={current_user.username}")
        
        # 转换为响应Schema
        return _convert_team_to_detail(team)
        
    except ValueError as e:
        logger.warning(f"⚠️ 团队创建失败: {str(e)}")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 团队创建异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("", response_model=TeamListResponse)
async def list_teams(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(20, ge=10, le=100, description="每页数量（10-100）"),
    status: Optional[str] = Query(None, description="状态筛选（draft/executing/completed/failed）"),
    keyword: Optional[str] = Query(None, description="关键词搜索（团队名称模糊匹配）"),
    sort_by: str = Query("update_time", description="排序字段（create_time/update_time/name）"),
    sort_order: str = Query("desc", description="排序方向（asc/desc）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """分页查询团队列表。
    
    支持多种筛选和排序方式，仅返回当前用户创建的团队。
    
    Args:
        page: 页码（默认: 1）
        page_size: 每页数量（默认: 20，范围: 10-100）
        status: 状态筛选（draft/executing/completed/failed）
        keyword: 关键词搜索（团队名称模糊匹配）
        sort_by: 排序字段（create_time/update_time/name）
        sort_order: 排序方向（asc/desc）
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        分页的团队列表（含最新执行信息）
        
    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/v1/teams?page=1&page_size=20&status=draft" \
          -H "Authorization: Bearer <token>"
        ```
    """
    try:
        # 调用服务层查询团队
        service = TeamService(db)
        teams, total = await service.list_teams(
            user_id=current_user.user_id,
            page=page,
            page_size=page_size,
            status=status,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # 转换为响应Schema
        team_summaries = [_convert_team_to_summary(team) for team in teams]
        
        return TeamListResponse(
            teams=team_summaries,
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages
            )
        )
        
    except Exception as e:
        logger.error(f"❌ 团队列表查询异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/{team_id}", response_model=TeamDetail)
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """获取团队完整配置详情。
    
    包含所有角色、任务和全局设置的详细信息。
    
    Args:
        team_id: 团队ID
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        完整的团队配置（含所有roles和tasks）
        
    Raises:
        HTTPException: 403 如果不是资源所有者
        HTTPException: 404 如果团队不存在
        
    Example:
        ```bash
        curl -X GET http://localhost:8000/api/v1/teams/team-code-review-001 \
          -H "Authorization: Bearer <token>"
        ```
    """
    try:
        # 调用服务层获取团队
        service = TeamService(db)
        team = await service.get_team_by_id(
            team_id=team_id,
            user_id=current_user.user_id
        )
        
        # 转换为响应Schema
        return _convert_team_to_detail(team)
        
    except ValueError as e:
        error_msg = str(e)
        if "无权访问" in error_msg:
            raise HTTPException(status_code=403, detail=error_msg)
        elif "不存在" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"❌ 团队详情查询异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.put("/{team_id}", response_model=TeamDetail)
async def update_team(
    team_id: str,
    data: UpdateTeamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新团队配置（支持乐观锁）。
    
    业务流程：
    1. 检查Read-Only锁（团队不能在执行中）
    2. 验证资源所有权
    3. 乐观锁校验（版本号匹配）
    4. 如果角色变更，同步更新Custom Agents
    5. 保存新版本快照
    6. 递增版本号
    
    Args:
        team_id: 团队ID
        data: 更新的团队配置（支持部分更新）
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        更新后的团队详情（版本号递增）
        
    Raises:
        HTTPException: 409 如果版本冲突（乐观锁失败）
        HTTPException: 403 如果不是资源所有者
        HTTPException: 423 如果团队正在执行中（Read-Only锁）
        
    Example:
        ```bash
        curl -X PUT http://localhost:8000/api/v1/teams/team-code-review-001 \
          -H "Authorization: Bearer <token>" \
          -H "If-Match: v0.1.0" \
          -H "Content-Type: application/json" \
          -d '{
            "name": "新版代码审查团队",
            "version": "v0.1.0"
          }'
        ```
    """
    try:
        # 调用服务层更新团队
        service = TeamService(db)
        team = await service.update_team(
            team_id=team_id,
            update_data=data.dict(exclude_unset=True),  # 仅传递设置的字段
            user_id=current_user.user_id,
            expected_version=data.version
        )
        
        logger.info(f"✅ 团队更新成功: team_id={team_id}, user={current_user.username}")
        
        # 转换为响应Schema
        return _convert_team_to_detail(team)
        
    except ValueError as e:
        error_msg = str(e)
        if "版本冲突" in error_msg:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "正在执行中" in error_msg:
            raise HTTPException(status_code=423, detail=error_msg)
        elif "无权访问" in error_msg:
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"❌ 团队更新异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
async def delete_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """软删除团队（标记deleted_at）。
    
    不会物理删除数据，而是标记deleted_at时间戳，便于后续恢复或审计。
    
    Args:
        team_id: 团队ID
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        删除成功消息
        
    Raises:
        HTTPException: 409 如果团队正在执行中
        HTTPException: 403 如果不是资源所有者
        
    Example:
        ```bash
        curl -X DELETE http://localhost:8000/api/v1/teams/team-code-review-001 \
          -H "Authorization: Bearer <token>"
        ```
    """
    try:
        # 调用服务层删除团队
        service = TeamService(db)
        await service.delete_team(
            team_id=team_id,
            user_id=current_user.user_id
        )
        
        logger.info(f"✅ 团队删除成功: team_id={team_id}, user={current_user.username}")
        
        return {"message": "团队已成功删除"}
        
    except ValueError as e:
        error_msg = str(e)
        if "正在执行中" in error_msg:
            raise HTTPException(status_code=409, detail=error_msg)
        elif "无权访问" in error_msg:
            raise HTTPException(status_code=403, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"❌ 团队删除异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/check-name", response_model=NameAvailabilityResponse)
async def check_name_availability(
    name: str = Query(..., description="待检查的团队名称"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """实时检查团队名称可用性。
    
    用于前端表单实时校验，避免提交时才发现名称冲突。
    
    Args:
        name: 待检查的团队名称
        db: 数据库会话
        current_user: 当前认证用户
        
    Returns:
        可用性状态及建议名称（如已被占用）
        
    Example:
        ```bash
        curl -X GET "http://localhost:8000/api/v1/teams/check-name?name=代码审查团队" \
          -H "Authorization: Bearer <token>"
        ```
        
        Response (可用):
        ```json
        {
          "available": true,
          "suggested_name": null
        }
        ```
        
        Response (已存在):
        ```json
        {
          "available": false,
          "suggested_name": "代码审查团队(2)"
        }
        ```
    """
    try:
        # 调用服务层检查名称
        service = TeamService(db)
        available, suggested_name = await service.check_name_availability(
            name=name,
            user_id=current_user.user_id
        )
        
        return NameAvailabilityResponse(
            available=available,
            suggested_name=suggested_name
        )
        
    except Exception as e:
        logger.error(f"❌ 名称检查异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


# ============================================================================
# 辅助函数
# ============================================================================

def _convert_team_to_detail(team: "Team") -> TeamDetail:
    """将Team ORM模型转换为TeamDetail Schema
    
    Args:
        team: Team ORM实例
        
    Returns:
        TeamDetail Schema实例
    """
    from deerteamx.api.schemas.team_schemas import (
        RoleConfig,
        TaskConfig,
        GlobalSettings,
    )
    
    config = team.config_snapshot
    
    # 解析roles
    roles = [
        RoleConfig(**role_data) 
        for role_data in config.get("roles", [])
    ]
    
    # 解析tasks
    tasks = [
        TaskConfig(**task_data) 
        for task_data in config.get("tasks", [])
    ]
    
    # 解析global_settings
    global_settings = GlobalSettings(**config.get("global_settings", {}))
    
    return TeamDetail(
        team_id=team.team_id,
        name=team.name,
        description=team.description,
        execution_mode=team.execution_mode,
        version=team.current_version,
        current_version_number=len(team.versions) if hasattr(team, 'versions') else 1,
        status=team.status,
        roles=roles,
        tasks=tasks,
        global_settings=global_settings,
        creator_id=team.creator_id,
        created_at=team.created_at,
        updated_at=team.updated_at
    )


def _convert_team_to_summary(team: "Team") -> TeamSummary:
    """将Team ORM模型转换为TeamSummary Schema
    
    Args:
        team: Team ORM实例
        
    Returns:
        TeamSummary Schema实例
    """
    return TeamSummary(
        team_id=team.team_id,
        name=team.name,
        execution_mode=team.execution_mode,
        status=team.status,
        creator_name=team.creator.username if team.creator else "Unknown",
        create_time=team.created_at,
        update_time=team.updated_at,
        latest_execution=None  # TODO: 查询最新执行记录
    )
