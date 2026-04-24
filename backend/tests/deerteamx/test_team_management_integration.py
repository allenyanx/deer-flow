"""Team Management Integration Tests

使用真实的 PostgreSQL 和 Redis 进行集成测试，验证团队管理模块的完整业务流程。

测试范围：
- 团队CRUD操作（创建/查询/更新/删除）
- 名称唯一性校验
- 版本管理与乐观锁
- 分页查询与筛选
- 权限控制与资源归属校验

所有测试直接操作真实数据库，确保数据一致性和完整性。
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from deerteamx.services.team_service import TeamService
from deerteamx.models.base import Base, Team, TeamVersion, User
from deerteamx.config.settings import get_settings


# ============================================================================
# 测试夹具（Fixtures）
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供所有异步测试使用"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """获取测试配置"""
    settings = get_settings()
    return settings


@pytest_asyncio.fixture
async def test_engine(test_settings):
    """创建测试数据库引擎
    
    使用独立的测试数据库或schema，避免污染开发数据。
    """
    # 使用配置文件中的DATABASE_URL
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=False,  # 关闭SQL日志输出
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


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """为每个测试创建独立的数据库会话
    
    每个测试执行后自动回滚，确保测试隔离性。
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.rollback()  # 测试结束后回滚
        finally:
            await session.close()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
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


@pytest.fixture
def sample_team_data():
    """示例团队配置数据"""
    return {
        "name": "代码审查团队",
        "description": "自动化代码审查工作流",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "code-scanner",
                "agent_name": "code_scanner_v1",
                "name": "代码扫描员",
                "goal": "扫描代码库中的潜在问题",
                "backstory": "资深代码审查专家",
                "model": "gpt-4-turbo",
                "temperature": 0.3,
                "max_tokens": 4096,
                "tool_groups": ["bash", "file_read"],
                "skills": ["ast-parser", "cve-database"],
                "memory_enabled": False,
                "verbose": False,
                "allow_delegation": False,
                "max_iter": 25,
                "max_retry_limit": 2
            }
        ],
        "tasks": [
            {
                "task_id": "scan-task",
                "description": "扫描指定目录的代码",
                "expected_output": "代码问题清单（JSON格式）",
                "assigned_role": "code-scanner",
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


@pytest.fixture
def team_service(db_session: AsyncSession) -> TeamService:
    """创建团队服务实例"""
    return TeamService(db_session)


# ============================================================================
# 团队创建测试
# ============================================================================

class TestCreateTeam:
    """团队创建功能测试"""
    
    @pytest.mark.asyncio
    async def test_create_team_success(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-001: 测试成功创建团队
        
        验证点：
        - 返回Team实例
        - version=v0.1.0
        - status=draft
        - creator_id正确
        - 数据库中确实创建了记录
        """
        # Act: 执行创建
        team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Assert: 验证结果
        assert team is not None
        assert team.name == sample_team_data["name"]
        assert team.execution_mode == sample_team_data["execution_mode"]
        assert team.status == "draft"
        assert team.creator_id == test_user.user_id
        assert team.current_version == "v0.1.0"
        assert team.description == sample_team_data["description"]
        assert team.team_id.startswith("team-")
        
        # 验证数据库中确实存在
        stmt = select(Team).where(Team.team_id == team.team_id)
        result = await team_service.db.execute(stmt)
        db_team = result.scalar_one_or_none()
        assert db_team is not None
        assert db_team.name == team.name
    
    @pytest.mark.asyncio
    async def test_create_team_duplicate_name_fails(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-002: 测试创建重名团队失败
        
        验证点：
        - 第一次创建成功
        - 第二次创建抛出ValueError
        - 错误消息包含"已存在"
        """
        # Arrange: 创建第一个团队
        await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act & Assert: 尝试创建同名团队
        with pytest.raises(ValueError, match="已存在"):
            await team_service.create_team(
                team_data=sample_team_data,  # 相同名称
                user_id=test_user.user_id
            )
    
    @pytest.mark.asyncio
    async def test_create_team_generates_unique_team_id(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-003: 测试生成的team_id唯一性
        
        验证点：
        - 多次创建同名团队（不同用户）生成不同team_id
        - team_id格式正确
        """
        # Arrange: 创建两个不同用户
        user1 = test_user
        user2 = User(
            user_id=uuid4(),
            username=f"test_user_2_{uuid4().hex[:8]}",
            password_hash="hash",
            email="user2@example.com",
            role_type="developer"
        )
        team_service.db.add(user2)
        await team_service.db.commit()
        
        # Act: 两个用户创建同名团队
        team_data = {
            "name": "同名团队",
            "description": "测试",
            "execution_mode": "static",
            "roles": [],
            "tasks": [],
            "global_settings": {"process_type": "sequential"}
        }
        
        team1 = await team_service.create_team(team_data=team_data, user_id=user1.user_id)
        team2 = await team_service.create_team(team_data=team_data, user_id=user2.user_id)
        
        # Assert
        assert team1.team_id != team2.team_id
        assert team1.team_id.startswith("team-")
        assert team2.team_id.startswith("team-")
    
    @pytest.mark.asyncio
    async def test_create_team_with_empty_description(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-004: 测试创建团队时description为空
        
        验证点：
        - description为None不影响创建
        - team.description为None
        """
        # Arrange
        team_data = {
            "name": "无描述团队",
            "description": None,
            "execution_mode": "static",
            "roles": [],
            "tasks": [],
            "global_settings": {"process_type": "sequential"}
        }
        
        # Act
        team = await team_service.create_team(
            team_data=team_data,
            user_id=test_user.user_id
        )
        
        # Assert
        assert team.description is None
    
    @pytest.mark.asyncio
    async def test_create_team_creates_version_snapshot(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-005: 测试创建团队时自动创建版本快照
        
        验证点：
        - team_versions表中有一条记录
        - version_number=1
        - version_tag=v0.1.0
        """
        # Act
        team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Assert: 查询版本快照
        stmt = select(TeamVersion).where(TeamVersion.team_id == team.team_id)
        result = await team_service.db.execute(stmt)
        versions = result.scalars().all()
        
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].version_tag == "v0.1.0"
        assert versions[0].change_summary == "初始版本"


# ============================================================================
# 团队查询测试
# ============================================================================

class TestGetTeam:
    """团队查询功能测试"""
    
    @pytest.mark.asyncio
    async def test_get_team_by_id_success(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-006: 测试成功获取团队详情
        
        验证点：
        - 返回Team实例
        - 所有字段正确
        """
        # Arrange: 先创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act: 查询团队
        team = await team_service.get_team_by_id(
            team_id=created_team.team_id,
            user_id=test_user.user_id
        )
        
        # Assert
        assert team.team_id == created_team.team_id
        assert team.name == sample_team_data["name"]
        assert team.creator_id == test_user.user_id
    
    @pytest.mark.asyncio
    async def test_get_team_by_id_not_found(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-007: 测试获取不存在的团队
        
        验证点：
        - 抛出ValueError
        - 错误消息包含"团队不存在"
        """
        # Act & Assert
        with pytest.raises(ValueError, match="团队不存在"):
            await team_service.get_team_by_id(
                team_id="team-nonexistent",
                user_id=test_user.user_id
            )
    
    @pytest.mark.asyncio
    async def test_get_team_by_id_unauthorized(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-008: 测试越权访问团队
        
        验证点：
        - 非创建者尝试访问
        - 抛出ValueError
        - 错误消息包含"无权访问"
        """
        # Arrange: 创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # 创建另一个用户
        other_user = User(
            user_id=uuid4(),
            username=f"other_user_{uuid4().hex[:8]}",
            password_hash="hash",
            email="other@example.com",
            role_type="developer"
        )
        team_service.db.add(other_user)
        await team_service.db.commit()
        
        # Act & Assert: 其他用户尝试访问
        with pytest.raises(ValueError, match="无权访问"):
            await team_service.get_team_by_id(
                team_id=created_team.team_id,
                user_id=other_user.user_id
            )
    
    @pytest.mark.asyncio
    async def test_list_teams_pagination(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-009: 测试分页查询团队列表
        
        验证点：
        - 返回正确的团队数量
        - total计算正确
        - 分页参数生效
        """
        # Arrange: 创建多个团队
        for i in range(5):
            team_data = {
                "name": f"测试团队{i+1}",
                "description": f"描述{i+1}",
                "execution_mode": "static",
                "roles": [],
                "tasks": [],
                "global_settings": {"process_type": "sequential"}
            }
            await team_service.create_team(team_data=team_data, user_id=test_user.user_id)
        
        # Act: 查询第1页，每页3条
        teams, total = await team_service.list_teams(
            user_id=test_user.user_id,
            page=1,
            page_size=3
        )
        
        # Assert
        assert len(teams) == 3
        assert total == 5
        
        # 查询第2页
        teams_page2, total_page2 = await team_service.list_teams(
            user_id=test_user.user_id,
            page=2,
            page_size=3
        )
        
        assert len(teams_page2) == 2
        assert total_page2 == 5
    
    @pytest.mark.asyncio
    async def test_list_teams_filter_by_status(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-010: 测试按状态筛选团队
        
        验证点：
        - 仅返回指定状态的团队
        """
        # Arrange: 创建不同状态的团队
        team_data_draft = {
            "name": "草稿团队",
            "description": "测试",
            "execution_mode": "static",
            "roles": [],
            "tasks": [],
            "global_settings": {"process_type": "sequential"}
        }
        await team_service.create_team(team_data=team_data_draft, user_id=test_user.user_id)
        
        # 手动修改一个团队的状态为executing（模拟）
        stmt = select(Team).where(Team.creator_id == test_user.user_id).limit(1)
        result = await team_service.db.execute(stmt)
        team = result.scalar_one()
        team.status = "executing"
        await team_service.db.commit()
        
        # Act: 查询draft状态的团队
        teams, total = await team_service.list_teams(
            user_id=test_user.user_id,
            status="draft"
        )
        
        # Assert
        assert all(t.status == "draft" for t in teams)
        assert total >= 1
    
    @pytest.mark.asyncio
    async def test_list_teams_search_by_keyword(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-011: 测试关键词搜索团队
        
        验证点：
        - 返回名称包含关键词的团队
        - 模糊匹配生效
        """
        # Arrange: 创建团队
        team_data = {
            "name": "Python代码审查",
            "description": "Python项目专用",
            "execution_mode": "static",
            "roles": [],
            "tasks": [],
            "global_settings": {"process_type": "sequential"}
        }
        await team_service.create_team(team_data=team_data, user_id=test_user.user_id)
        
        # Act: 搜索包含"Python"的团队
        teams, total = await team_service.list_teams(
            user_id=test_user.user_id,
            keyword="Python"
        )
        
        # Assert
        assert total >= 1
        assert any("Python" in team.name for team in teams)


# ============================================================================
# 团队更新测试
# ============================================================================

class TestUpdateTeam:
    """团队更新功能测试"""
    
    @pytest.mark.asyncio
    async def test_update_team_name_success(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-012: 测试成功更新团队名称
        
        验证点：
        - name更新
        - 版本号递增
        - 创建新版本快照
        """
        # Arrange: 创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act: 更新名称
        updated_team = await team_service.update_team(
            team_id=created_team.team_id,
            update_data={"name": "新名称"},
            user_id=test_user.user_id
        )
        
        # Assert
        assert updated_team.name == "新名称"
        assert updated_team.current_version == "v0.1.1"  # 版本号递增
        
        # 验证版本快照
        stmt = select(func.count()).select_from(
            select(TeamVersion).where(TeamVersion.team_id == created_team.team_id).subquery()
        )
        result = await team_service.db.execute(stmt)
        version_count = result.scalar()
        assert version_count == 2  # 初始版本 + 更新版本
    
    @pytest.mark.asyncio
    async def test_update_team_optimistic_lock_conflict(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-013: 测试乐观锁冲突
        
        验证点：
        - expected_version与current_version不匹配
        - 抛出ValueError
        """
        # Arrange: 创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act & Assert: 使用错误的版本号更新
        with pytest.raises(ValueError, match="版本冲突"):
            await team_service.update_team(
                team_id=created_team.team_id,
                update_data={"name": "新名称"},
                user_id=test_user.user_id,
                expected_version="v0.0.1"  # 错误的版本号
            )
    
    @pytest.mark.asyncio
    async def test_update_team_executing_locked(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-014: 测试更新执行中的团队被锁定
        
        验证点：
        - status="executing"时拒绝更新
        - 抛出ValueError
        """
        # Arrange: 创建团队并设置为executing
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        created_team.status = "executing"
        await team_service.db.commit()
        
        # Act & Assert
        with pytest.raises(ValueError, match="正在执行中"):
            await team_service.update_team(
                team_id=created_team.team_id,
                update_data={"name": "新名称"},
                user_id=test_user.user_id
            )
    
    @pytest.mark.asyncio
    async def test_update_team_partial_update(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-015: 测试部分字段更新
        
        验证点：
        - 仅更新指定字段
        - 其他字段保持不变
        """
        # Arrange: 创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        original_name = created_team.name
        
        # Act: 仅更新description
        updated_team = await team_service.update_team(
            team_id=created_team.team_id,
            update_data={"description": "新描述"},
            user_id=test_user.user_id
        )
        
        # Assert
        assert updated_team.description == "新描述"
        assert updated_team.name == original_name  # 名称不变


# ============================================================================
# 团队删除测试
# ============================================================================

class TestDeleteTeam:
    """团队删除功能测试"""
    
    @pytest.mark.asyncio
    async def test_delete_team_soft_delete(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-016: 测试成功软删除团队
        
        验证点：
        - deleted_at设置为当前时间
        - status改为"failed"
        - 数据库中记录仍存在
        """
        # Arrange: 创建团队
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act: 删除团队
        await team_service.delete_team(
            team_id=created_team.team_id,
            user_id=test_user.user_id
        )
        
        # Assert: 查询数据库
        stmt = select(Team).where(Team.team_id == created_team.team_id)
        result = await team_service.db.execute(stmt)
        deleted_team = result.scalar_one()
        
        assert deleted_team.deleted_at is not None
        assert deleted_team.status == "failed"
    
    @pytest.mark.asyncio
    async def test_delete_team_executing_blocked(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-017: 测试删除执行中的团队被拦截
        
        验证点：
        - status="executing"时拒绝删除
        - 抛出ValueError
        """
        # Arrange: 创建团队并设置为executing
        created_team = await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        created_team.status = "executing"
        await team_service.db.commit()
        
        # Act & Assert
        with pytest.raises(ValueError, match="正在执行中"):
            await team_service.delete_team(
                team_id=created_team.team_id,
                user_id=test_user.user_id
            )


# ============================================================================
# 名称检查测试
# ============================================================================

class TestCheckNameAvailability:
    """名称可用性检查测试"""
    
    @pytest.mark.asyncio
    async def test_check_name_available(self, team_service: TeamService, test_user: User):
        """TC-TEAM-IT-018: 测试名称可用
        
        验证点：
        - available=True
        - suggested_name=None
        """
        # Act
        available, suggested_name = await team_service.check_name_availability(
            name="全新团队名称",
            user_id=test_user.user_id
        )
        
        # Assert
        assert available is True
        assert suggested_name is None
    
    @pytest.mark.asyncio
    async def test_check_name_unavailable_with_suggestion(self, team_service: TeamService, sample_team_data, test_user: User):
        """TC-TEAM-IT-019: 测试名称不可用并生成建议名称
        
        验证点：
        - available=False
        - suggested_name不为None
        """
        # Arrange: 创建团队
        await team_service.create_team(
            team_data=sample_team_data,
            user_id=test_user.user_id
        )
        
        # Act: 检查同名
        available, suggested_name = await team_service.check_name_availability(
            name=sample_team_data["name"],
            user_id=test_user.user_id
        )
        
        # Assert
        assert available is False
        assert suggested_name is not None
        assert sample_team_data["name"] in suggested_name


# ============================================================================
# 辅助方法测试
# ============================================================================

class TestHelperMethods:
    """辅助方法测试"""
    
    @pytest.mark.asyncio
    async def test_increment_version_normal(self, team_service: TeamService):
        """TC-TEAM-IT-020: 测试版本号递增
        
        验证点：
        - v0.1.0 → v0.1.1
        - v1.2.10 → v1.2.11
        """
        # Act & Assert
        assert team_service._increment_version("v0.1.0") == "v0.1.1"
        assert team_service._increment_version("v1.2.10") == "v1.2.11"
    
    @pytest.mark.asyncio
    async def test_increment_version_invalid_format(self, team_service: TeamService):
        """TC-TEAM-IT-021: 测试非法版本号格式降级
        
        验证点：
        - 非法格式返回默认版本v0.1.0
        """
        # Act & Assert
        assert team_service._increment_version("invalid") == "v0.1.0"
    
    @pytest.mark.asyncio
    async def test_generate_change_summary(self, team_service: TeamService):
        """TC-TEAM-IT-022: 测试生成变更说明
        
        验证点：
        - 多字段变更时用"；"分隔
        """
        # Act
        summary = team_service._generate_change_summary({
            "name": "新名称",
            "description": "新描述"
        })
        
        # Assert
        assert "修改名称" in summary
        assert "修改描述" in summary

