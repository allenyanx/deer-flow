"""DeerTeamX 分布式锁管理器。

该模块提供基于 PostgreSQL 的轻量级分布式锁实现，
用于在多用户协作场景下保护团队配置不被并发修改。
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, select, update, delete
from sqlalchemy.sql import func

from deerteamx.models.base import Base

logger = logging.getLogger(__name__)


class LockManager:
    """团队配置读写锁管理器。"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def acquire_lock(self, team_id: str, user_id: str, ttl_seconds: int = 300) -> bool:
        """尝试获取团队配置的写锁。
        
        Args:
            team_id: 团队标识。
            user_id: 请求锁的用户标识。
            ttl_seconds: 锁的自动过期时间（秒），防止死锁。
            
        Returns:
            是否成功获取锁。
        """
        now = datetime.now(timezone.utc)
        
        # 1. 尝试插入或更新锁记录 (Upsert 逻辑)
        # 如果锁不存在，或者锁已过期，则允许获取
        stmt = (
            update(LockRecord)
            .where(
                LockRecord.team_id == team_id,
                (LockRecord.expires_at < now) | (LockRecord.owner_id == user_id)
            )
            .values(
                owner_id=user_id,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                lock_token=str(uuid.uuid4())
            )
        )
        result = await self.db.execute(stmt)
        
        if result.rowcount > 0:
            await self.db.commit()
            logger.info(f"Lock acquired for team {team_id} by user {user_id}")
            return True
        
        # 2. 如果更新失败，尝试插入新记录（处理首次加锁情况）
        try:
            new_lock = LockRecord(
                team_id=team_id,
                owner_id=user_id,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                lock_token=str(uuid.uuid4())
            )
            self.db.add(new_lock)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            logger.warning(f"Failed to acquire lock for team {team_id}, already locked by another user")
            return False

    async def release_lock(self, team_id: str, user_id: str) -> bool:
        """释放指定的锁。"""
        stmt = delete(LockRecord).where(
            LockRecord.team_id == team_id,
            LockRecord.owner_id == user_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def is_locked(self, team_id: str) -> Optional[str]:
        """检查团队是否处于锁定状态。
        
        Returns:
            如果已锁定，返回当前持有锁的用户 ID；否则返回 None。
        """
        now = datetime.now(timezone.utc)
        stmt = select(LockRecord.owner_id).where(
            LockRecord.team_id == team_id,
            LockRecord.expires_at > now
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def acquire_execution_lock(self, team_id: str, execution_id: str, ttl_seconds: int = 1800) -> bool:
        """尝试获取执行锁（Read-Only 锁）。
        
        Args:
            team_id: 团队标识。
            execution_id: 执行ID作为锁的持有者标识。
            ttl_seconds: 锁的自动过期时间（秒），默认30分钟。
            
        Returns:
            是否成功获取锁。
        """
        now = datetime.now(timezone.utc)
        
        # 1. 尝试插入或更新锁记录 (Upsert 逻辑)
        # 如果锁不存在，或者锁已过期，则允许获取
        stmt = (
            update(LockRecord)
            .where(
                LockRecord.team_id == team_id,
                (LockRecord.expires_at < now) | (LockRecord.owner_id == execution_id)
            )
            .values(
                owner_id=execution_id,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                lock_token=str(uuid.uuid4())
            )
        )
        result = await self.db.execute(stmt)
        
        if result.rowcount > 0:
            await self.db.commit()
            logger.info(f"Execution lock acquired for team {team_id} by execution {execution_id}")
            return True
        
        # 2. 如果更新失败，尝试插入新记录（处理首次加锁情况）
        try:
            new_lock = LockRecord(
                team_id=team_id,
                owner_id=execution_id,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
                lock_token=str(uuid.uuid4())
            )
            self.db.add(new_lock)
            await self.db.commit()
            logger.info(f"Execution lock acquired for team {team_id} by execution {execution_id}")
            return True
        except Exception:
            await self.db.rollback()
            logger.warning(f"Failed to acquire execution lock for team {team_id}, already locked")
            return False

    async def release_execution_lock(self, team_id: str, execution_id: str) -> bool:
        """释放执行锁。
        
        Args:
            team_id: 团队标识。
            execution_id: 执行ID（锁持有者）。
            
        Returns:
            是否成功释放锁。
        """
        stmt = delete(LockRecord).where(
            LockRecord.team_id == team_id,
            LockRecord.owner_id == execution_id
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Execution lock released for team {team_id} by execution {execution_id}")
            return True
        else:
            logger.warning(f"Lock not found or already released for team {team_id}")
            return False

    async def get_execution_lock_owner(self, team_id: str) -> Optional[str]:
        """查询执行锁的持有者。
        
        Args:
            team_id: 团队标识。
            
        Returns:
            如果已锁定，返回执行ID；否则返回 None。
        """
        now = datetime.now(timezone.utc)
        stmt = select(LockRecord.owner_id).where(
            LockRecord.team_id == team_id,
            LockRecord.expires_at > now
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


class LockRecord(Base):
    """数据库锁记录模型。"""
    __tablename__ = "team_locks"

    team_id = Column(String(64), primary_key=True)
    owner_id = Column(String(64), nullable=False)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    lock_token = Column(String(64), nullable=False)
