"""Team Management Service Unit Tests

测试团队管理服务的核心功能：
- 团队CRUD操作
- 名称唯一性校验
- 版本管理
- 乐观锁控制
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from deerteamx.services.team_service import TeamService
from deerteamx.models.base import Team, TeamVersion, User


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_user():
    """创建示例用户"""
    return User(
        user_id=uuid4(),
        username="test_user",
        password_hash="hashed_password",
        email="test@example.com",
        role_type="developer"
    )


@pytest.fixture
def sample_team_data():
    """创建示例团队配置数据"""
    return {
        "name": "测试团队",
        "description": "用于单元测试的团队",
        "execution_mode": "static",
        "roles": [
            {
                "role_id": "role-1",
                "agent_name": "agent_1",
                "name": "角色1",
                "goal": "测试目标",
                "backstory": "测试背景",
                "model": "gpt-4",
                "tool_groups": ["web_search"],
                "skills": ["skill-1"]
            }
        ],
        "tasks": [
            {
                "task_id": "task-1",
                "description": "测试任务",
                "expected_output": "预期输出",
                "assigned_role": "role-1",
                "dependencies": []
            }
        ],
        "global_settings": {
            "process_type": "sequential",
            "verbose": False,
            "cache_enabled": True
        }
    }


@pytest.fixture
def team_service(mock_db_session):
    """创建团队服务实例"""
    with patch('deerteamx.services.team_service.get_settings') as mock_settings, \
         patch('deerteamx.services.team_service.get_kms') as mock_kms:
        
        mock_settings.return_value.ENCRYPTION_MASTER_KEY = "test_key_32_chars_long_test_key"
        mock_kms.return_value = MagicMock()
        
        service = TeamService(mock_db_session)
        return service


# ============================================================================
# 团队创建测试
# ============================================================================

class TestCreateTeam:
    """团队创建功能测试"""
    
    @pytest.mark.asyncio
    async def test_create_team_success(self, team_service, mock_db_session, sample_team_data, sample_user):
        """测试成功创建团队"""
        # Mock名称唯一性检查
        with patch.object(team_service, '_validate_team_name_unique', new_callable=AsyncMock):
            # Mock Custom Agent同步
            with patch.object(team_service, '_sync_custom_agents', new_callable=AsyncMock):
                # Mock版本快照创建
                with patch.object(team_service, '_create_version_snapshot', new_callable=AsyncMock):
                    # Mock数据库操作
                    mock_db_session.flush = AsyncMock()
                    mock_db_session.commit = AsyncMock()
                    mock_db_session.refresh = AsyncMock()
                    
                    # 执行创建
                    team = await team_service.create_team(
                        team_data=sample_team_data,
                        user_id=sample_user.user_id
                    )
                    
                    # 验证结果
                    assert team is not None
                    assert team.name == sample_team_data["name"]
                    assert team.execution_mode == sample_team_data["execution_mode"]
                    assert team.status == "draft"
                    assert team.creator_id == sample_user.user_id
                    assert team.current_version == "v0.1.0"
                    
                    # 验证数据库调用
                    mock_db_session.add.assert_called()
                    mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_team_duplicate_name(self, team_service, sample_team_data, sample_user):
        """测试创建重名团队失败"""
        # Mock名称唯一性检查抛出异常
        with patch.object(team_service, '_validate_team_name_unique', new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = ValueError("团队名称 '测试团队' 已存在")
            
            # 执行创建并期望异常
            with pytest.raises(ValueError, match="已存在"):
                await team_service.create_team(
                    team_data=sample_team_data,
                    user_id=sample_user.user_id
                )
    
    @pytest.mark.asyncio
    async def test_create_team_generates_valid_team_id(self, team_service, mock_db_session, sample_team_data, sample_user):
        """测试生成的team_id格式正确"""
        with patch.object(team_service, '_validate_team_name_unique', new_callable=AsyncMock), \
             patch.object(team_service, '_sync_custom_agents', new_callable=AsyncMock), \
             patch.object(team_service, '_create_version_snapshot', new_callable=AsyncMock):
            
            mock_db_session.flush = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            
            team = await team_service.create_team(
                team_data=sample_team_data,
                user_id=sample_user.user_id
            )
            
            # 验证team_id格式: team-{slug}-{uuid8}
            assert team.team_id.startswith("team-")
            parts = team.team_id.split("-")
            assert len(parts) >= 3  # team + slug + uuid


# ============================================================================
# 团队查询测试
# ============================================================================

class TestGetTeam:
    """团队查询功能测试"""
    
    @pytest.mark.asyncio
    async def test_get_team_by_id_success(self, team_service, mock_db_session, sample_user):
        """测试成功获取团队详情"""
        # 创建模拟团队
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="draft",
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        # Mock数据库查询
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # 执行查询
        team = await team_service.get_team_by_id(
            team_id="team-test-123",
            user_id=sample_user.user_id
        )
        
        # 验证结果
        assert team is not None
        assert team.team_id == "team-test-123"
        assert team.name == "测试团队"
    
    @pytest.mark.asyncio
    async def test_get_team_not_found(self, team_service, mock_db_session):
        """测试获取不存在的团队"""
        # Mock数据库返回None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # 执行查询并期望异常
        with pytest.raises(ValueError, match="团队不存在"):
            await team_service.get_team_by_id(
                team_id="team-nonexistent",
                user_id=uuid4()
            )
    
    @pytest.mark.asyncio
    async def test_get_team_permission_denied(self, team_service, mock_db_session, sample_user):
        """测试无权访问其他用户的团队"""
        other_user_id = uuid4()
        
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="draft",
            creator_id=other_user_id,  # 不同用户
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # 执行查询并期望异常
        with pytest.raises(ValueError, match="无权访问"):
            await team_service.get_team_by_id(
                team_id="team-test-123",
                user_id=sample_user.user_id
            )


# ============================================================================
# 团队列表测试
# ============================================================================

class TestListTeams:
    """团队列表查询测试"""
    
    @pytest.mark.asyncio
    async def test_list_teams_with_pagination(self, team_service, mock_db_session, sample_user):
        """测试分页查询团队列表"""
        # Mock数据库查询
        mock_teams = [
            Team(
                team_id=f"team-test-{i}",
                name=f"测试团队{i}",
                execution_mode="static",
                status="draft",
                creator_id=sample_user.user_id,
                current_version="v0.1.0",
                config_snapshot={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_teams
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock总数查询
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        
        # 执行查询
        teams, total = await team_service.list_teams(
            user_id=sample_user.user_id,
            page=1,
            page_size=10
        )
        
        # 验证结果
        assert len(teams) == 5
        assert total == 5


# ============================================================================
# 团队更新测试
# ============================================================================

class TestUpdateTeam:
    """团队更新功能测试"""
    
    @pytest.mark.asyncio
    async def test_update_team_success(self, team_service, mock_db_session, sample_user):
        """测试成功更新团队"""
        # 创建模拟团队
        mock_team = Team(
            team_id="team-test-123",
            name="原名称",
            execution_mode="static",
            status="draft",
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={"name": "原名称"}
        )
        
        # Mock get_team_by_id
        with patch.object(team_service, 'get_team_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_team
            
            # Mock名称唯一性检查
            with patch.object(team_service, '_validate_team_name_unique', new_callable=AsyncMock):
                # Mock版本号和快照创建
                with patch.object(team_service, '_get_next_version_number', new_callable=AsyncMock) as mock_version:
                    mock_version.return_value = 2
                    
                    with patch.object(team_service, '_create_version_snapshot', new_callable=AsyncMock):
                        mock_db_session.flush = AsyncMock()
                        mock_db_session.commit = AsyncMock()
                        mock_db_session.refresh = AsyncMock()
                        
                        # 执行更新
                        update_data = {"name": "新名称"}
                        updated_team = await team_service.update_team(
                            team_id="team-test-123",
                            update_data=update_data,
                            user_id=sample_user.user_id
                        )
                        
                        # 验证结果
                        assert updated_team.name == "新名称"
                        assert updated_team.current_version == "v0.2.0"  # 版本号递增
    
    @pytest.mark.asyncio
    async def test_update_team_executing_locked(self, team_service, sample_user):
        """测试更新正在执行的团队失败"""
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="executing",  # 正在执行
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        with patch.object(team_service, 'get_team_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_team
            
            # 执行更新并期望异常
            with pytest.raises(ValueError, match="正在执行中"):
                await team_service.update_team(
                    team_id="team-test-123",
                    update_data={"name": "新名称"},
                    user_id=sample_user.user_id
                )
    
    @pytest.mark.asyncio
    async def test_update_team_version_conflict(self, team_service, sample_user):
        """测试乐观锁版本冲突"""
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="draft",
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        with patch.object(team_service, 'get_team_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_team
            
            # 执行更新并期望异常（期望v0.2.0但实际是v0.1.0）
            with pytest.raises(ValueError, match="版本冲突"):
                await team_service.update_team(
                    team_id="team-test-123",
                    update_data={"name": "新名称"},
                    user_id=sample_user.user_id,
                    expected_version="v0.2.0"
                )


# ============================================================================
# 团队删除测试
# ============================================================================

class TestDeleteTeam:
    """团队删除功能测试"""
    
    @pytest.mark.asyncio
    async def test_delete_team_success(self, team_service, mock_db_session, sample_user):
        """测试成功删除团队"""
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="draft",
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        with patch.object(team_service, 'get_team_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_team
            
            mock_db_session.commit = AsyncMock()
            
            # 执行删除
            await team_service.delete_team(
                team_id="team-test-123",
                user_id=sample_user.user_id
            )
            
            # 验证软删除标记
            assert mock_team.deleted_at is not None
            assert mock_team.status == "failed"
            mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_team_executing_locked(self, team_service, sample_user):
        """测试删除正在执行的团队失败"""
        mock_team = Team(
            team_id="team-test-123",
            name="测试团队",
            execution_mode="static",
            status="executing",  # 正在执行
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        with patch.object(team_service, 'get_team_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_team
            
            # 执行删除并期望异常
            with pytest.raises(ValueError, match="正在执行中"):
                await team_service.delete_team(
                    team_id="team-test-123",
                    user_id=sample_user.user_id
                )


# ============================================================================
# 名称唯一性测试
# ============================================================================

class TestNameAvailability:
    """团队名称唯一性测试"""
    
    @pytest.mark.asyncio
    async def test_check_name_available(self, team_service, mock_db_session, sample_user):
        """测试名称可用"""
        # Mock数据库返回None（无重名）
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # 执行检查
        available, suggested_name = await team_service.check_name_availability(
            name="新团队名称",
            user_id=sample_user.user_id
        )
        
        # 验证结果
        assert available is True
        assert suggested_name is None
    
    @pytest.mark.asyncio
    async def test_check_name_unavailable(self, team_service, mock_db_session, sample_user):
        """测试名称不可用"""
        # Mock数据库返回已有团队
        mock_existing_team = Team(
            team_id="team-existing",
            name="重复名称",
            execution_mode="static",
            status="draft",
            creator_id=sample_user.user_id,
            current_version="v0.1.0",
            config_snapshot={}
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing_team
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock建议名称生成
        with patch.object(team_service, '_generate_suggested_name', return_value="重复名称(2)"):
            # 执行检查
            available, suggested_name = await team_service.check_name_availability(
                name="重复名称",
                user_id=sample_user.user_id
            )
            
            # 验证结果
            assert available is False
            assert suggested_name == "重复名称(2)"


# ============================================================================
# 版本号管理测试
# ============================================================================

class TestVersionManagement:
    """版本号管理测试"""
    
    def test_increment_version_patch(self, team_service):
        """测试递增patch版本号"""
        new_version = team_service._increment_version("v0.1.0")
        assert new_version == "v0.1.1"
    
    def test_increment_version_minor(self, team_service):
        """测试递增minor版本号（当前实现仅递增patch）"""
        new_version = team_service._increment_version("v0.2.5")
        assert new_version == "v0.2.6"
    
    def test_increment_version_invalid_format(self, team_service):
        """测试无效版本格式处理"""
        new_version = team_service._increment_version("invalid")
        assert new_version == "v0.1.0"  # 返回默认版本
    
    def test_generate_team_id_format(self, team_service):
        """测试team_id生成格式"""
        team_id = team_service._generate_team_id("测试团队")
        
        assert team_id.startswith("team-")
        assert len(team_id.split("-")) >= 3
    
    def test_generate_suggested_name_sequence(self, team_service, mock_db_session, sample_user):
        """测试建议名称序号递增"""
        # Mock数据库返回已有名称
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["测试团队(1)", "测试团队(2)"]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        suggested = team_service._generate_suggested_name("测试团队", sample_user.user_id)
        
        # 应该返回下一个可用序号
        assert suggested == "测试团队(3)"
