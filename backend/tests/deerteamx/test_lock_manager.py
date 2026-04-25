"""DeerTeamX 分布式锁管理器单元测试。

该模块测试 LockManager 的执行锁功能，包括：
- 锁的获取和释放
- 锁超时自动失效
- 锁冲突处理
- 并发场景下的锁行为
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.runtime.lock_manager import LockManager, LockRecord
from deerteamx.models.base import User, Team


class TestExecutionLock:
    """执行锁（Read-Only 锁）测试套件。"""

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """创建测试用户。"""
        user = User(
            user_id=uuid4(),
            username=f"test_user_{uuid4().hex[:8]}",
            password_hash="dummy_hash",
            role_type="developer"
        )
        db_session.add(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def test_team(self, db_session: AsyncSession, test_user: User):
        """创建测试团队。"""
        team = Team(
            team_id=f"team_test_{uuid4().hex[:8]}",
            name=f"测试团队_{uuid4().hex[:8]}",
            execution_mode="static",
            status="draft",
            creator_id=test_user.user_id,
            config_snapshot={
                "roles": [{"role_id": "r1", "agent_name": "test-agent"}],
                "tasks": [{"task_id": "t1", "dependencies": []}]
            }
        )
        db_session.add(team)
        await db_session.commit()
        return team

    @pytest.fixture
    def lock_manager(self, db_session: AsyncSession):
        """创建锁管理器实例。"""
        return LockManager(db_session)

    async def test_acquire_execution_lock_success(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试成功获取执行锁。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 获取锁
        locked = await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id,
            ttl_seconds=1800  # 30分钟
        )
        
        assert locked is True
        
        # 验证锁记录已创建
        current_owner = await lock_manager.get_execution_lock_owner(test_team.team_id)
        assert current_owner == execution_id

    async def test_acquire_execution_lock_conflict(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试锁冲突 - 同一团队已被锁定。"""
        execution_id_1 = f"exec-test-1-{uuid4().hex[:8]}"
        execution_id_2 = f"exec-test-2-{uuid4().hex[:8]}"
        team_id = test_team.team_id  # 提前获取 team_id，避免 lazy loading
        
        # 第一个执行获取锁
        locked_1 = await lock_manager.acquire_execution_lock(
            team_id=team_id,
            execution_id=execution_id_1,
            ttl_seconds=1800
        )
        assert locked_1 is True
        
        # 第二个执行尝试获取锁应该失败
        locked_2 = await lock_manager.acquire_execution_lock(
            team_id=team_id,
            execution_id=execution_id_2,
            ttl_seconds=1800
        )
        assert locked_2 is False
        
        # 验证锁仍然由第一个执行持有
        current_owner = await lock_manager.get_execution_lock_owner(team_id)
        assert current_owner == execution_id_1

    async def test_release_execution_lock_success(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试成功释放执行锁。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 获取锁
        await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id,
            ttl_seconds=1800
        )
        
        # 释放锁
        released = await lock_manager.release_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id
        )
        
        assert released is True
        
        # 验证锁已释放
        current_owner = await lock_manager.get_execution_lock_owner(test_team.team_id)
        assert current_owner is None

    async def test_release_execution_lock_not_found(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试释放不存在的锁。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 尝试释放未持有的锁
        released = await lock_manager.release_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id
        )
        
        assert released is False

    async def test_execution_lock_auto_expire(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试锁自动过期（30分钟超时）。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 获取一个即将过期的锁（1秒后过期）
        locked = await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id,
            ttl_seconds=1  # 1秒后过期
        )
        assert locked is True
        
        # 等待锁过期
        import asyncio
        await asyncio.sleep(1.5)
        
        # 验证锁已过期，可以被其他执行获取
        current_owner = await lock_manager.get_execution_lock_owner(test_team.team_id)
        assert current_owner is None
        
        # 新的执行可以获取锁
        execution_id_2 = f"exec-test-2-{uuid4().hex[:8]}"
        locked_2 = await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id_2,
            ttl_seconds=1800
        )
        assert locked_2 is True

    async def test_get_execution_lock_owner(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试查询锁持有者。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 初始状态无锁
        owner = await lock_manager.get_execution_lock_owner(test_team.team_id)
        assert owner is None
        
        # 获取锁
        await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id,
            ttl_seconds=1800
        )
        
        # 验证可以查询到锁持有者
        owner = await lock_manager.get_execution_lock_owner(test_team.team_id)
        assert owner == execution_id

    async def test_multiple_teams_independent_locks(self, db_session: AsyncSession, lock_manager: LockManager, test_user: User):
        """TC-EXEC-007: 测试不同团队的锁相互独立。"""
        # 创建两个团队
        team_1 = Team(
            team_id=f"team_test_1_{uuid4().hex[:8]}",
            name=f"测试团队1_{uuid4().hex[:8]}",
            execution_mode="static",
            status="draft",
            creator_id=test_user.user_id,
            config_snapshot={"roles": [], "tasks": []}
        )
        team_2 = Team(
            team_id=f"team_test_2_{uuid4().hex[:8]}",
            name=f"测试团队2_{uuid4().hex[:8]}",
            execution_mode="static",
            status="draft",
            creator_id=test_user.user_id,
            config_snapshot={"roles": [], "tasks": []}
        )
        db_session.add_all([team_1, team_2])
        await db_session.commit()
        
        execution_id_1 = f"exec-test-1-{uuid4().hex[:8]}"
        execution_id_2 = f"exec-test-2-{uuid4().hex[:8]}"
        
        # 团队1获取锁
        locked_1 = await lock_manager.acquire_execution_lock(
            team_id=team_1.team_id,
            execution_id=execution_id_1,
            ttl_seconds=1800
        )
        assert locked_1 is True
        
        # 团队2也应该能获取锁（互不影响）
        locked_2 = await lock_manager.acquire_execution_lock(
            team_id=team_2.team_id,
            execution_id=execution_id_2,
            ttl_seconds=1800
        )
        assert locked_2 is True
        
        # 验证两个团队的锁各自独立
        owner_1 = await lock_manager.get_execution_lock_owner(team_1.team_id)
        owner_2 = await lock_manager.get_execution_lock_owner(team_2.team_id)
        assert owner_1 == execution_id_1
        assert owner_2 == execution_id_2

    async def test_lock_ttl_default_30_minutes(self, db_session: AsyncSession, lock_manager: LockManager, test_team: Team):
        """TC-EXEC-007: 测试默认 TTL 为 30 分钟（1800秒）。"""
        execution_id = f"exec-test-{uuid4().hex[:8]}"
        
        # 使用默认 TTL 获取锁
        await lock_manager.acquire_execution_lock(
            team_id=test_team.team_id,
            execution_id=execution_id
            # 不指定 ttl_seconds，使用默认值 1800
        )
        
        # 查询锁记录的 expires_at
        from sqlalchemy import select
        stmt = select(LockRecord).where(LockRecord.team_id == test_team.team_id)
        result = await db_session.execute(stmt)
        lock_record = result.scalar_one_or_none()
        
        assert lock_record is not None
        
        # 验证过期时间在合理范围内（30分钟左右）
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(seconds=1800)
        time_diff = abs((lock_record.expires_at - expected_expiry).total_seconds())
        
        # 允许 5 秒的误差（由于执行时间）
        assert time_diff < 5, f"Lock expiry time {lock_record.expires_at} is not within 5 seconds of expected {expected_expiry}"
