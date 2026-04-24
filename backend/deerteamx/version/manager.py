"""DeerTeamX 版本管理器。

该模块负责处理团队配置的语义化版本递增、快照存储及历史查询逻辑。
"""

import logging
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from deerteamx.models.base import TeamVersion, Team

logger = logging.getLogger(__name__)


class VersionManager:
    """团队配置版本管理核心类。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_version(
        self, 
        team_id: str, 
        config: dict, 
        user_id: str, 
        change_type: str = "patch",
        message: Optional[str] = None
    ) -> TeamVersion:
        """创建新的配置版本快照。
        
        Args:
            team_id: 团队标识。
            config: 当前的团队配置字典。
            user_id: 操作用户标识。
            change_type: 变更类型 (major/minor/patch)。
            message: 变更说明。
            
        Returns:
            创建的 TeamVersion 实例。
        """
        # 1. 获取当前最新版本号
        last_version = await self._get_latest_version(team_id)
        new_tag = self._bump_version(last_version.version_tag if last_version else "v0.0.0", change_type)

        # 2. 创建并保存快照
        version = TeamVersion(
            team_id=team_id,
            version_tag=new_tag,
            change_type=change_type,
            config_snapshot=config,
            commit_message=message,
            created_by=user_id
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        
        logger.info(f"Created version {new_tag} for team {team_id}")
        return version

    async def get_version_history(self, team_id: str, limit: int = 50) -> List[TeamVersion]:
        """获取团队版本历史记录。"""
        stmt = (
            select(TeamVersion)
            .where(TeamVersion.team_id == team_id)
            .order_by(desc(TeamVersion.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_version_detail(self, team_id: str, version_tag: str) -> Optional[TeamVersion]:
        """获取指定版本的详细信息（含配置快照）。"""
        stmt = select(TeamVersion).where(
            TeamVersion.team_id == team_id,
            TeamVersion.version_tag == version_tag
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def rollback_to_version(self, team_id: str, version_tag: str, user_id: str) -> Dict[str, Any]:
        """回滚到指定版本。
        
        注意：此方法仅返回目标版本的配置，实际更新团队配置需由调用方执行。
        """
        target_version = await self.get_version_detail(team_id, version_tag)
        if not target_version:
            raise ValueError(f"Version {version_tag} not found for team {team_id}")
        
        # 创建一个新的版本记录来标记这次回滚操作
        await self.create_version(
            team_id=team_id,
            config=target_version.config_snapshot,
            user_id=user_id,
            change_type="patch",
            message=f"Rollback to {version_tag}"
        )
        
        return {
            "target_config": target_version.config_snapshot,
            "rollback_version_tag": target_version.version_tag
        }

    async def _get_latest_version(self, team_id: str) -> Optional[TeamVersion]:
        """查询团队的最新版本记录。"""
        stmt = (
            select(TeamVersion)
            .where(TeamVersion.team_id == team_id)
            .order_by(desc(TeamVersion.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _bump_version(current_tag: str, change_type: str) -> str:
        """根据变更类型递增语义化版本号。"""
        # 去除 'v' 前缀
        version_str = current_tag.lstrip('v')
        try:
            major, minor, patch = map(int, version_str.split('.'))
        except ValueError:
            major, minor, patch = 0, 0, 0

        if change_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif change_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        return f"v{major}.{minor}.{patch}"
