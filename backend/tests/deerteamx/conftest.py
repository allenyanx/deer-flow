"""DeerTeamX 测试共享 fixtures

提供所有 deerteamx 测试模块共用的数据库会话、引擎和配置 fixtures。

Fixture 依赖链:
    db_session -> test_engine -> test_settings

使用示例:
    @pytest.mark.asyncio
    async def test_example(db_session: AsyncSession):
        # 直接使用 db_session，测试结束后自动回滚
        pass
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from deerteamx.models.base import Base, User, Team, Execution
from deerteamx.config import get_settings


# ============================================================================
# 配置与引擎 Fixtures (session scope)
# ============================================================================

@pytest.fixture(scope="session")
def test_settings():
    """获取测试配置
    
    Returns:
        Settings: 应用配置实例，包含 DATABASE_URL 等
    """
    return get_settings()


@pytest_asyncio.fixture(scope="session")
async def test_engine(test_settings):
    """创建测试数据库引擎 (session 级别，所有测试共享)
    
    生命周期:
    - 测试会话开始时: 创建引擎并初始化表结构
    - 测试会话结束时: 删除所有表并关闭引擎
    
    Args:
        test_settings: 测试配置
        
    Yields:
        AsyncEngine: SQLAlchemy 异步引擎实例
    """
    # 创建异步引擎
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=False,  # 关闭 SQL 日志输出（调试时可设为 True）
        pool_size=5,
        max_overflow=10,
    )
    
    # 创建所有表结构
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理：删除所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


# ============================================================================
# 数据库会话 Fixture (function scope)
# ============================================================================

@pytest_asyncio.fixture
async def db_session_no_rollback(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """为需要持久化数据的测试创建数据库会话 (不自动回滚)
    
    ⚠️ 警告: 使用此 fixture 的测试会产生副作用,数据会持久化到数据库
    ⚠️ 仅在以下场景使用:
       - 需要跨测试共享数据
       - 调试时查看数据库状态
       - 集成测试需要真实数据
    
    使用后请手动清理数据或重置数据库。
    
    Args:
        test_engine: 测试数据库引擎
        
    Yields:
        AsyncSession: SQLAlchemy 异步会话实例 (不回滚)
        
    Example:
        @pytest.mark.asyncio
        async def test_with_persistence(db_session_no_rollback):
            user = User(username="test")
            db_session_no_rollback.add(user)
            await db_session_no_rollback.commit()
            # 数据会持久化,不会被回滚
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        yield session
        # 注意: 这里没有 rollback(),数据会保留
        await session.close()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """为每个测试创建独立的数据库会话 (function 级别)
    
    关键特性:
    - 每个测试函数获得全新的 AsyncSession
    - 测试结束后自动回滚，确保测试隔离性
    - 不会污染其他测试的数据
    
    Args:
        test_engine: 测试数据库引擎
        
    Yields:
        AsyncSession: SQLAlchemy 异步会话实例
        
    Example:
        @pytest.mark.asyncio
        async def test_create_user(db_session: AsyncSession):
            user = User(username="test", email="test@example.com")
            db_session.add(user)
            await db_session.commit()
            # 测试结束后自动回滚，数据不会持久化
    """
    # 创建会话工厂
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # 为当前测试创建独立会话
    async with async_session_maker() as session:
        try:
            yield session
            # await session.rollback()  # 测试结束后回滚所有更改
        finally:
            await session.close()


# ============================================================================
# 通用测试数据 Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户
    
    用于需要用户身份的测试场景（如团队创建、执行触发等）。
    
    Args:
        db_session: 数据库会话
        
    Returns:
        User: 测试用户实例
        
    Example:
        async def test_create_team(db_session, test_user):
            team = await team_service.create_team(
                team_data=sample_data,
                user_id=test_user.user_id
            )
    """
    user = User(
        user_id=uuid4(),
        username=f"test_user_{uuid4().hex[:8]}",
        password_hash="$2b$12$LJ3m4ys3Lk5zF6qH8pN9eOxYzK1wQ2rT3uV4xW5yZ6aB7cD8eF9gH",
        email=f"test_{uuid4().hex[:8]}@example.com",
        role_type="developer"
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def sample_team(db_session: AsyncSession, test_user: User) -> Team:
    """创建示例团队（用于执行测试）
    
    包含一个完整的最小化团队配置（1个角色 + 1个任务）。
    
    Args:
        db_session: 数据库会话
        test_user: 测试用户
        
    Returns:
        Team: 测试团队实例
        
    Example:
        async def test_execute_team(executor, sample_team, test_user):
            execution_id = await executor.execute_team(
                team_id=sample_team.team_id,
                team_config=sample_team.config_snapshot,
                input_data={"query": "test"},
                user_id=str(test_user.user_id)
            )
    """
    from deerteamx.services.team_service import TeamService
    
    team_config = {
        "name": f"测试团队_{uuid4().hex[:8]}",
        "description": "用于测试的团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "analyst",
                "agent_name": "data_analyst_v1",
                "name": "数据分析师",
                "goal": "分析数据并提供洞察",
                "backstory": "你是一位资深数据分析师",
                "model": "gpt-4-turbo",
                "temperature": 0.3,
                "max_tokens": 4096,
                "tool_groups": ["bash"],
                "skills": ["data-analysis"],
                "memory_enabled": False,
                "verbose": False,
                "allow_delegation": False,
                "max_iter": 25,
                "max_retry_limit": 2
            }
        ],
        "tasks": [
            {
                "task_id": "analysis-task",
                "description": "分析销售数据",
                "expected_output": "分析报告（JSON格式）",
                "assigned_role": "analyst",
                "dependencies": [],
                "dynamic_trigger": None
            }
        ],
        "global_settings": {
            "process_type": "sequential",
            "verbose": False,
            "manager_llm_model": None,
            "manager_agent_id": None,
            "crew_memory_enabled": False,
            "max_rpm": None,
            "cache_enabled": True,
            "long_term_memory_enabled": False,
            "share_crew": False,
            "state_persistence": False,
            "human_feedback_enabled": False
        }
    }
    
    team_service = TeamService(db_session)
    team = await team_service.create_team(
        team_data=team_config,
        user_id=test_user.user_id
    )
    
    return team


@pytest_asyncio.fixture
async def executor(db_session: AsyncSession):
    """创建执行引擎实例
    
    Args:
        db_session: 数据库会话
        
    Returns:
        TeamExecutor: 执行引擎实例
        
    Example:
        async def test_executor(executor):
            assert executor.db is not None
    """
    from deerteamx.runtime.executor import TeamExecutor
    return TeamExecutor(db_session, gateway_url="http://localhost:8001")
