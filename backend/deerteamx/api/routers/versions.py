"""DeerTeamX 版本管理 API 路由。

该模块提供团队配置的版本查询、差异对比及回滚功能接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.database import get_db
from deerteamx.version.manager import VersionManager
from deerteamx.version.diff import DiffEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/teams/{team_id}/versions", tags=["versions"])


@router.get("")
async def list_versions(
    team_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取团队版本历史列表。"""
    manager = VersionManager(db)
    versions = await manager.get_version_history(team_id, limit)
    
    return {
        "versions": [v.to_dict() for v in versions],
        "total": len(versions)
    }


@router.get("/{version_tag}")
async def get_version_detail(team_id: str, version_tag: str, db: AsyncSession = Depends(get_db)):
    """获取指定版本的详细配置快照。"""
    manager = VersionManager(db)
    version = await manager.get_version_detail(team_id, version_tag)
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return {
        **version.to_dict(),
        "config_snapshot": version.config_snapshot
    }


@router.get("/compare/{base_tag}...{target_tag}")
async def compare_versions(
    team_id: str,
    base_tag: str,
    target_tag: str,
    db: AsyncSession = Depends(get_db)
):
    """对比两个版本之间的配置差异。"""
    manager = VersionManager(db)
    
    base_ver = await manager.get_version_detail(team_id, base_tag)
    target_ver = await manager.get_version_detail(team_id, target_tag)
    
    if not base_ver or not target_ver:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    
    # 计算差异
    diff_result = DiffEngine.calculate_diff(base_ver.config_snapshot, target_ver.config_snapshot)
    formatted_diff = DiffEngine.format_diff_for_ui(diff_result)
    
    return {
        "base_version": base_tag,
        "target_version": target_tag,
        "changes": formatted_diff,
        "raw_diff": diff_result
    }


@router.post("/{version_tag}/rollback")
async def rollback_version(
    team_id: str,
    version_tag: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = "test-user" # 实际应从 JWT Token 中提取
):
    """执行版本回滚操作。"""
    try:
        manager = VersionManager(db)
        result = await manager.rollback_to_version(team_id, version_tag, user_id)
        
        return {
            "message": f"Successfully prepared rollback to {version_tag}",
            "new_config": result["target_config"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during rollback")
