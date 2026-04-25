"""DeerTeamX 断点续传功能单元测试。

该模块测试执行中断恢复功能，包括：
- Checkpoint 保存和查询
- 待执行任务计算
- 从断点恢复执行
- 边界场景处理
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.runtime.executor import TeamExecutor
from deerteamx.models.base import User, Team, Execution, ExecutionState


class TestBreakpointResume:
    """断点续传功能测试套件。"""

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
                "roles": [
                    {"role_id": "r1", "agent_name": "analyst"},
                    {"role_id": "r2", "agent_name": "reviewer"}
                ],
                "tasks": [
                    {"task_id": "t1", "assigned_role": "r1", "dependencies": []},
                    {"task_id": "t2", "assigned_role": "r2", "dependencies": ["t1"]},
                    {"task_id": "t3", "assigned_role": "r1", "dependencies": ["t2"]}
                ]
            }
        )
        db_session.add(team)
        await db_session.commit()
        return team

    @pytest.fixture
    async def test_execution(self, db_session: AsyncSession, test_team: Team, test_user: User):
        """创建测试执行记录。"""
        execution = Execution(
            execution_id=f"exec-test-{uuid4().hex[:8]}",
            team_id=test_team.team_id,
            thread_id=f"thread-{uuid4().hex}",
            status="pending",
            input_data={"query": "测试查询"},
            created_by=test_user.user_id
        )
        db_session.add(execution)
        await db_session.commit()
        return execution

    @pytest.fixture
    def executor(self, db_session: AsyncSession):
        """创建执行器实例。"""
        return TeamExecutor(db_session)

    # ========================================================================
    # Checkpoint 保存测试
    # ========================================================================

    async def test_save_execution_state_new_record(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试保存新的执行状态记录。"""
        state_id = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed",
            output_data={"result": "success"}
        )
        
        assert state_id > 0
        
        # 验证记录已保存
        from sqlalchemy import select
        stmt = select(ExecutionState).where(ExecutionState.state_id == state_id)
        result = await db_session.execute(stmt)
        state = result.scalar_one_or_none()
        
        assert state is not None
        assert state.task_id == "t1"
        assert state.role_id == "r1"
        assert state.status == "completed"
        assert state.output_data == {"result": "success"}
        assert state.completed_at is not None

    async def test_save_execution_state_update_existing(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试更新已有的执行状态记录。"""
        # 先创建 running 状态
        state_id_1 = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="running"
        )
        
        # 更新为 completed
        state_id_2 = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed",
            output_data={"result": "done"}
        )
        
        # 应该是同一条记录
        assert state_id_1 == state_id_2
        
        # 验证状态已更新
        from sqlalchemy import select
        stmt = select(ExecutionState).where(ExecutionState.state_id == state_id_1)
        result = await db_session.execute(stmt)
        state = result.scalar_one_or_none()
        
        assert state.status == "completed"
        assert state.output_data == {"result": "done"}
        assert state.completed_at is not None

    async def test_save_execution_state_with_error(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试保存失败的任务状态。"""
        state_id = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="failed",
            error_message="Task failed due to timeout"
        )
        
        assert state_id > 0
        
        from sqlalchemy import select
        stmt = select(ExecutionState).where(ExecutionState.state_id == state_id)
        result = await db_session.execute(stmt)
        state = result.scalar_one_or_none()
        
        assert state.status == "failed"
        assert state.error_message == "Task failed due to timeout"

    # ========================================================================
    # Checkpoint 查询测试
    # ========================================================================

    async def test_get_last_checkpoint_single_task(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试获取单个任务的 checkpoint。"""
        # 保存一个完成的任务
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed",
            output_data={"data": "test"}
        )
        
        checkpoint = await executor._get_last_checkpoint(test_execution.execution_id)
        
        assert checkpoint is not None
        assert checkpoint["task_id"] == "t1"
        assert checkpoint["role_id"] == "r1"
        assert checkpoint["output_data"] == {"data": "test"}

    async def test_get_last_checkpoint_multiple_tasks(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试获取多个任务中最后的 checkpoint。"""
        import asyncio
        
        # 保存三个完成的任务
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed"
        )
        
        # 稍微延迟确保时间戳不同
        await asyncio.sleep(0.1)
        
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t2",
            role_id="r2",
            status="completed"
        )
        
        await asyncio.sleep(0.1)
        
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t3",
            role_id="r1",
            status="completed"
        )
        
        # 应该返回最后一个（t3）
        checkpoint = await executor._get_last_checkpoint(test_execution.execution_id)
        
        assert checkpoint is not None
        assert checkpoint["task_id"] == "t3"

    async def test_get_last_checkpoint_no_completed_tasks(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试没有完成任务时返回 None。"""
        # 只保存 running 状态的任务
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="running"
        )
        
        checkpoint = await executor._get_last_checkpoint(test_execution.execution_id)
        
        assert checkpoint is None

    async def test_get_last_checkpoint_only_failed_tasks(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试只有失败任务时返回 None。"""
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="failed",
            error_message="Error"
        )
        
        checkpoint = await executor._get_last_checkpoint(test_execution.execution_id)
        
        assert checkpoint is None

    # ========================================================================
    # 待执行任务计算测试
    # ========================================================================

    async def test_get_pending_tasks_no_checkpoint(self, db_session: AsyncSession, executor: TeamExecutor, test_team: Team):
        """TC-EXEC-011: 测试没有 checkpoint 时返回所有任务。"""
        team_config = test_team.config_snapshot
        
        pending = await executor._get_pending_tasks(
            execution_id="exec-test",
            team_config=team_config,
            last_checkpoint=None
        )
        
        assert len(pending) == 3
        assert pending[0]["task_id"] == "t1"
        assert pending[1]["task_id"] == "t2"
        assert pending[2]["task_id"] == "t3"

    async def test_get_pending_tasks_from_middle(self, db_session: AsyncSession, executor: TeamExecutor, test_team: Team):
        """TC-EXEC-011: 测试从中间任务恢复时的待执行任务。"""
        team_config = test_team.config_snapshot
        
        last_checkpoint = {
            "task_id": "t1",
            "role_id": "r1",
            "output_data": {},
            "completed_at": datetime.now(timezone.utc)
        }
        
        pending = await executor._get_pending_tasks(
            execution_id="exec-test",
            team_config=team_config,
            last_checkpoint=last_checkpoint
        )
        
        assert len(pending) == 2
        assert pending[0]["task_id"] == "t2"
        assert pending[1]["task_id"] == "t3"

    async def test_get_pending_tasks_from_last_task(self, db_session: AsyncSession, executor: TeamExecutor, test_team: Team):
        """TC-EXEC-011: 测试从最后一个任务恢复时返回空列表。"""
        team_config = test_team.config_snapshot
        
        last_checkpoint = {
            "task_id": "t3",
            "role_id": "r1",
            "output_data": {},
            "completed_at": datetime.now(timezone.utc)
        }
        
        pending = await executor._get_pending_tasks(
            execution_id="exec-test",
            team_config=team_config,
            last_checkpoint=last_checkpoint
        )
        
        assert len(pending) == 0

    async def test_get_pending_tasks_invalid_task_id(self, db_session: AsyncSession, executor: TeamExecutor, test_team: Team):
        """TC-EXEC-011: 测试 checkpoint 中的 task_id 不存在时返回空列表。"""
        team_config = test_team.config_snapshot
        
        last_checkpoint = {
            "task_id": "t999",  # 不存在的任务
            "role_id": "r1",
            "output_data": {},
            "completed_at": datetime.now(timezone.utc)
        }
        
        pending = await executor._get_pending_tasks(
            execution_id="exec-test",
            team_config=team_config,
            last_checkpoint=last_checkpoint
        )
        
        assert len(pending) == 0

    # ========================================================================
    # 恢复执行测试
    # ========================================================================

    async def test_resume_execution_no_checkpoint(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试没有 checkpoint 时无法恢复。"""
        team_config = {
            "roles": [{"role_id": "r1", "agent_name": "test"}],
            "tasks": [{"task_id": "t1", "dependencies": []}]
        }
        
        success = await executor._resume_execution(
            execution_id=test_execution.execution_id,
            team_config=team_config,
            input_data={"query": "test"}
        )
        
        assert success is False

    async def test_resume_execution_all_completed(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution, test_team: Team):
        """TC-EXEC-011: 测试所有任务已完成时标记为 completed。"""
        team_config = test_team.config_snapshot
        
        # 模拟所有任务都已完成
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t3",  # 最后一个任务
            role_id="r1",
            status="completed"
        )
        
        success = await executor._resume_execution(
            execution_id=test_execution.execution_id,
            team_config=team_config,
            input_data={"query": "test"}
        )
        
        # 应该成功（因为没有待执行任务，直接标记为完成）
        assert success is True
        
        # 验证 execution 状态已更新
        from sqlalchemy import select
        stmt = select(Execution).where(Execution.execution_id == test_execution.execution_id)
        result = await db_session.execute(stmt)
        execution = result.scalar_one_or_none()
        
        assert execution.status == "completed"

    # ========================================================================
    # 边界场景测试
    # ========================================================================

    async def test_save_state_auto_timestamps(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试自动设置时间戳。"""
        before = datetime.now(timezone.utc)
        
        state_id = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="running"
        )
        
        after = datetime.now(timezone.utc)
        
        from sqlalchemy import select
        stmt = select(ExecutionState).where(ExecutionState.state_id == state_id)
        result = await db_session.execute(stmt)
        state = result.scalar_one_or_none()
        
        assert state.started_at is not None
        assert before <= state.started_at <= after
        assert state.completed_at is None  # running 状态不应有 completed_at

    async def test_multiple_states_same_execution(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试同一执行的多个状态记录。"""
        # 保存多个任务的状态
        state_1 = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed"
        )
        
        state_2 = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t2",
            role_id="r2",
            status="completed"
        )
        
        state_3 = await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t3",
            role_id="r1",
            status="running"
        )
        
        # 应该有3条不同的记录
        assert state_1 != state_2
        assert state_2 != state_3
        
        # 查询所有状态
        from sqlalchemy import select
        stmt = (
            select(ExecutionState)
            .where(ExecutionState.execution_id == test_execution.execution_id)
            .order_by(ExecutionState.state_id)
        )
        result = await db_session.execute(stmt)
        states = result.scalars().all()
        
        assert len(states) == 3

    async def test_checkpoint_cascade_delete(self, db_session: AsyncSession, executor: TeamExecutor, test_execution: Execution):
        """TC-EXEC-011: 测试删除 execution 时级联删除 states。"""
        # 保存一些状态
        await executor._save_execution_state(
            execution_id=test_execution.execution_id,
            task_id="t1",
            role_id="r1",
            status="completed"
        )
        
        # 删除 execution
        from sqlalchemy import delete
        stmt = delete(Execution).where(Execution.execution_id == test_execution.execution_id)
        await db_session.execute(stmt)
        await db_session.commit()
        
        # 验证 states 也被删除
        from sqlalchemy import select
        stmt = select(ExecutionState).where(ExecutionState.execution_id == test_execution.execution_id)
        result = await db_session.execute(stmt)
        states = result.scalars().all()
        
        assert len(states) == 0
